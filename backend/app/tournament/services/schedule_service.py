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
)
from app.tournament.repositories import (
    TournamentRepository,
    TournamentDateRepository,
    TournamentTeamRepository,
    MatchRepository,
    MatchResultVersionRepository,
    GroupStandingRepository,
    ScheduleVersionRepository,
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
        effective_bo = bo_format or config.get("bo_format", BOFormat.BO1.value)
        if effective_bo not in [e.value for e in BOFormat]:
            effective_bo = BOFormat.BO1.value
        existing_matches = await self.match_repo.get_by_tournament(tournament_id)
        # Only delete group stage matches, preserve bracket matches
        for m in existing_matches:
            if m.stage == MatchStage.GROUP_STAGE:
                await self.match_repo.delete(m.id)
        team_list = [t.team_id for t in teams]
        random.seed(None)
        random.shuffle(team_list)
        matches_to_schedule = []
        for i in range(0, len(team_list) - 1, 2):
            matches_to_schedule.append((team_list[i], team_list[i + 1]))
        # Include bracket matches if they exist
        bracket_matches = [m for m in existing_matches if m.stage == MatchStage.KNOCKOUT]
        if bracket_matches:
            matches_to_schedule.extend([(m.team_a_id, m.team_b_id) for m in bracket_matches if m.team_a_id and m.team_b_id])
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
        if not slots:
            raise ValueError("No time slots available")
        schedule = []
        team_last_end: Dict[str, datetime] = {}
        team_match_count: Dict[str, int] = {t: 0 for t in team_list}
        date_match_count: Dict[date, int] = {}
        slot_idx = 0
        for team_a, team_b in matches_to_schedule:
            placed = False
            for i in range(len(slots)):
                idx = (slot_idx + i) % len(slots)
                slot = slots[idx]
                if not slot["available"]:
                    continue
                slot_start = datetime.combine(slot["date"], slot["start"])
                slot_end = datetime.combine(slot["date"], slot["end"])
                conflict_a = team_a in team_last_end and (slot_start - team_last_end[team_a]).total_seconds() < effective_min_rest * 60
                conflict_b = team_b in team_last_end and (slot_start - team_last_end[team_b]).total_seconds() < effective_min_rest * 60
                if conflict_a or conflict_b:
                    continue
                team_last_end[team_a] = slot_end
                team_last_end[team_b] = slot_end
                team_match_count[team_a] += 1
                team_match_count[team_b] += 1
                date_match_count[slot["date"]] = date_match_count.get(slot["date"], 0) + 1
                await self.match_repo.create(
                    {
                        "tournament_id": tournament_id,
                        "stage": MatchStage.GROUP_STAGE,
                        "scheduled_date": slot["date"],
                        "start_time": slot["start"],
                        "end_time": slot["end"],
                        "team_a_id": team_a,
                        "team_b_id": team_b,
                        "format": effective_bo,
                        "status": MatchStatus.SCHEDULED,
                    }
                )
                schedule.append({
                    "date": slot["date"].isoformat(),
                    "start_time": slot["start"].isoformat(),
                    "end_time": slot["end"].isoformat(),
                    "team_a_id": team_a,
                    "team_b_id": team_b,
                    "format": effective_bo,
                })
                slots[idx]["available"] = False
                slot_idx = (idx + 1) % len(slots)
                placed = True
                break
            if not placed:
                pass
        total_matches = len(schedule)
        total_days = len(dates)
        rest_gaps = []
        for team in team_list:
            team_matches = await self.match_repo.get_by_tournament(tournament_id, MatchStage.GROUP_STAGE)
            team_sorted = sorted(
                [m for m in team_matches if m.team_a_id == team or m.team_b_id == team],
                key=lambda m: (m.scheduled_date, m.start_time),
            )
            for j in range(len(team_sorted) - 1):
                m1 = team_sorted[j]
                m2 = team_sorted[j + 1]
                end1 = datetime.combine(m1.scheduled_date, m1.end_time)
                start2 = datetime.combine(m2.scheduled_date, m2.start_time)
                gap = (start2 - end1).total_seconds() / 60.0
                rest_gaps.append(gap)
        min_rest_gap = min(rest_gaps) if rest_gaps else None
        avg_rest_gap = sum(rest_gaps) / len(rest_gaps) if rest_gaps else None
        max_rest_gap = max(rest_gaps) if rest_gaps else None
        conflicts = sum(1 for gap in rest_gaps if gap < effective_min_rest)
        fairness_score = self._compute_fairness_score(rest_gaps, team_match_count, date_match_count)
        await self.save_schedule_version(tournament_id, created_by=created_by, notes="Auto-generated schedule")
        tournament.status = "SCHEDULE_GENERATED"
        tournament.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(tournament)
        return ScheduleGenerateResponse(
            total_matches=total_matches,
            total_days=total_days,
            min_rest_gap=min_rest_gap,
            avg_rest_gap=avg_rest_gap,
            max_rest_gap=max_rest_gap,
            conflict_count=conflicts,
            constraint_violations=[],
            fairness_score=fairness_score,
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
