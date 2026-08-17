from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict, Any, Tuple
import json
import random

from sqlalchemy.ext.asyncio import AsyncSession

from app.tournament.models.tournament_models import (
    Tournament,
    TournamentDate,
    TournamentTeam,
    Match,
    MatchResultVersion,
    GroupStanding,
    ScheduleVersion,
    TournamentGroup,
    TournamentGroupMember,
)
from app.tournament.repositories import (
    TournamentRepository,
    TournamentDateRepository,
    TournamentTeamRepository,
    MatchRepository,
    MatchResultVersionRepository,
    GroupStandingRepository,
    ScheduleVersionRepository,
    TournamentGroupRepository,
    TournamentGroupMemberRepository,
)
from app.tournament.schemas.tournament_schemas import ScheduleGenerateResponse
from app.tournament.constants import MatchStatus, MatchStage, BOFormat


class ScheduleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tournament_repo = TournamentRepository(db)
        self.date_repo = TournamentDateRepository(db)
        self.team_repo = TournamentTeamRepository(db)
        self.match_repo = MatchRepository(db)
        self.result_version_repo = MatchResultVersionRepository(db)
        self.standing_repo = GroupStandingRepository(db)
        self.schedule_version_repo = ScheduleVersionRepository(db)
        self.group_repo = TournamentGroupRepository(db)
        self.group_member_repo = TournamentGroupMemberRepository(db)

    async def generate_schedule(
        self,
        tournament_id: str,
        created_by: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        match_duration_minutes: Optional[int] = None,
        bo_format: Optional[str] = None,
        min_rest_minutes: Optional[int] = None,
        buffer_minutes: Optional[int] = None,
        assign_times: bool = False,
    ) -> ScheduleGenerateResponse:
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")
        dates = await self.date_repo.get_by_tournament(tournament_id)
        if not dates:
            raise ValueError("No tournament dates configured")
        teams = await self.team_repo.get_by_tournament(tournament_id)
        if len(teams) < 2:
            raise ValueError("At least 2 teams required")
        config = {}
        if tournament.config_json:
            try:
                config = json.loads(tournament.config_json)
            except Exception:
                config = {}
        effective_min_rest = min_rest_minutes if min_rest_minutes is not None else config.get("min_rest_minutes", 60)
        effective_buffer = buffer_minutes if buffer_minutes is not None else config.get("buffer_minutes", 0)
        effective_match_duration = match_duration_minutes if match_duration_minutes is not None else config.get("match_duration_minutes", 45)
        group_bo = BOFormat.BO1.value
        existing_matches = await self.match_repo.get_by_tournament(tournament_id)
        # Only delete group stage matches, preserve bracket matches
        for m in existing_matches:
            if m.stage == MatchStage.GROUP_STAGE:
                await self.match_repo.delete(m.id)
        # Generate group stage matches from groups
        groups = await self.group_repo.get_by_tournament(tournament_id)
        matches_to_schedule = []
        for group in groups:
            members = await self.group_member_repo.get_by_group(group.id)
            member_teams = [m.tournament_team.team_id for m in members if m.tournament_team and m.tournament_team.team_id]
            if len(member_teams) < 2:
                continue
            # Round-robin: each team plays every other team once
            for i in range(len(member_teams)):
                for j in range(i + 1, len(member_teams)):
                    matches_to_schedule.append((member_teams[i], member_teams[j], group.id, MatchStage.GROUP_STAGE, group_bo))
        # Include bracket matches if they exist
        bracket_matches = [m for m in existing_matches if m.stage == MatchStage.KNOCKOUT]
        bracket_match_map = {m.match_number: m for m in bracket_matches if m.match_number is not None}
        if bracket_match_map:
            for match_num, match in bracket_match_map.items():
                matches_to_schedule.append((match.team_a_id, match.team_b_id, None, MatchStage.KNOCKOUT, match.format))
        # If no group matches and no bracket matches, create at least some structure
        if not matches_to_schedule and len(teams) >= 2:
            team_list = [t.team_id for t in teams]
            for i in range(0, len(team_list) - 1, 2):
                matches_to_schedule.append((team_list[i], team_list[i + 1], None, MatchStage.GROUP_STAGE, group_bo))
        slots = []
        for date_obj in dates:
            if start_date and date_obj.date < start_date:
                continue
            if end_date and date_obj.date > end_date:
                continue
            current = datetime.combine(date_obj.date, date_obj.start_time)
            end = datetime.combine(date_obj.date, date_obj.end_time)
            slot_duration = timedelta(minutes=effective_match_duration + effective_buffer)
            while current + timedelta(minutes=effective_match_duration) <= end:
                slots.append({
                    "date": date_obj.date,
                    "start": current.time(),
                    "end": (current + timedelta(minutes=effective_match_duration)).time(),
                    "available": True,
                })
                current += slot_duration
        schedule = []
        slot_idx = 0
        for item in matches_to_schedule:
            team_a, team_b, group_id, stage, fmt = item
            if assign_times and slots:
                placed = False
                for i in range(len(slots)):
                    idx = (slot_idx + i) % len(slots)
                    slot = slots[idx]
                    if not slot["available"]:
                        continue
                    slot_start = datetime.combine(slot["date"], slot["start"])
                    slot_end = datetime.combine(slot["date"], slot["end"])
                    team_last_end = {}
                    # simple rest check
                    team_matches = await self.match_repo.get_by_tournament(tournament_id, stage)
                    conflict = False
                    for m in team_matches:
                        if m.team_a_id == team_a or m.team_b_id == team_a:
                            m_end = datetime.combine(m.scheduled_date or date(2000,1,1), m.end_time or time(0,0))
                            if (slot_start - m_end).total_seconds() < effective_min_rest * 60:
                                conflict = True
                                break
                    if conflict:
                        continue
                    await self.match_repo.create({
                        "tournament_id": tournament_id,
                        "stage": stage,
                        "group_id": group_id,
                        "scheduled_date": slot["date"],
                        "start_time": slot["start"],
                        "end_time": slot["end"],
                        "team_a_id": team_a,
                        "team_b_id": team_b,
                        "format": fmt,
                        "status": MatchStatus.SCHEDULED,
                    })
                    schedule.append({
                        "date": slot["date"].isoformat(),
                        "start_time": slot["start"].isoformat(),
                        "end_time": slot["end"].isoformat(),
                        "team_a_id": team_a,
                        "team_b_id": team_b,
                        "format": fmt,
                    })
                    slots[idx]["available"] = False
                    slot_idx = (idx + 1) % len(slots)
                    placed = True
                    break
                if not placed:
                    pass
            else:
                await self.match_repo.create({
                    "tournament_id": tournament_id,
                    "stage": stage,
                    "group_id": group_id,
                    "team_a_id": team_a,
                    "team_b_id": team_b,
                    "format": fmt,
                    "status": MatchStatus.SCHEDULED,
                })
                schedule.append({
                    "team_a_id": team_a,
                    "team_b_id": team_b,
                    "format": fmt,
                })
        total_matches = len(schedule)
        total_days = len(dates)
        await self.save_schedule_version(tournament_id, created_by=created_by, notes="Auto-generated schedule")
        tournament.status = TournamentStatus.SCHEDULE_GENERATED
        tournament.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(tournament)
        return ScheduleGenerateResponse(
            total_matches=total_matches,
            total_days=total_days,
            min_rest_gap=None,
            avg_rest_gap=None,
            max_rest_gap=None,
            conflict_count=0,
            constraint_violations=[],
            fairness_score=0.0,
            warnings=[],
            schedule=schedule,
        )

    def _compute_fairness_score(self, rest_gaps: List[float], team_match_count: Dict[str, int], date_match_count: Dict[date, int]) -> float:
        if not rest_gaps:
            return 0.0
        rest_fairness = 1.0
        if len(rest_gaps) > 1:
            avg_gap = sum(rest_gaps) / len(rest_gaps)
            variance = sum((g - avg_gap) ** 2 for g in rest_gaps) / len(rest_gaps)
            std = variance ** 0.5
            rest_fairness = max(0.0, 1.0 - (std / (avg_gap + 1e-6)))
        match_counts = list(team_match_count.values())
        daily_counts = list(date_match_count.values())
        daily_balance = 1.0
        if daily_counts:
            avg_daily = sum(daily_counts) / len(daily_counts)
            if avg_daily > 0:
                daily_balance = 1.0 - (max(daily_counts) - min(daily_counts)) / avg_daily
        score = 0.4 * rest_fairness + 0.3 * max(0.0, daily_balance) + 0.3 * 0.8
        return round(max(0.0, min(1.0, score)), 2)

    async def get_schedule(self, tournament_id: str) -> List[Match]:
        return await self.match_repo.get_by_tournament(tournament_id)

    async def get_schedule_versions(self, tournament_id: str) -> List[ScheduleVersion]:
        return await self.schedule_version_repo.get_by_tournament(tournament_id)
