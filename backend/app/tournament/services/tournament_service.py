
from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict, Any
import json
import random

from sqlalchemy.ext.asyncio import AsyncSession

from app.tournament.models.tournament_models import (
    Tournament,
    TournamentDate,
    TournamentTeam,
    TournamentGroup,
    TournamentGroupMember,
    Match,
    MatchResultVersion,
    GroupStanding,
    KnockoutBracket,
    KnockoutRound,
    KnockoutSlot,
    ScheduleVersion,
    TournamentPlacement,
)
from app.tournament.repositories import (
    TournamentRepository,
    TournamentDateRepository,
    TournamentTeamRepository,
    TournamentGroupRepository,
    TournamentGroupMemberRepository,
    MatchRepository,
    MatchResultVersionRepository,
    GroupStandingRepository,
    KnockoutBracketRepository,
    KnockoutRoundRepository,
    KnockoutSlotRepository,
    ScheduleVersionRepository,
    TournamentPlacementRepository,
)
from app.tournament.schemas.tournament_schemas import (
    TournamentCreate,
    TournamentUpdate,
    TournamentTeamSelect,
    TournamentGroupCreate,
    TournamentGroupUpdate,
    MatchCreate,
    MatchUpdate,
    StandingsOverride,
    PlacementSet,
    ScheduleGenerateResponse,
)
from app.tournament.schemas.tournament_schemas import (
    TournamentCreate,
    TournamentUpdate,
    TournamentTeamSelect,
    TournamentGroupCreate,
    TournamentGroupUpdate,
    MatchCreate,
    MatchUpdate,
    MatchResultSubmit,
    StandingsOverride,
    PlacementSet,
    ScheduleGenerateResponse,
)
from app.tournament.constants import (
    TournamentStatus,
    MatchStage,
    MatchStatus,
    BOFormat,
    BO_WIN_REQUIREMENTS,
    can_transition,
    BracketType,
    ThirdPlaceMode,
)
from app.api.deps import get_current_user


class TournamentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tournament_repo = TournamentRepository(db)
        self.date_repo = TournamentDateRepository(db)
        self.team_repo = TournamentTeamRepository(db)
        self.group_repo = TournamentGroupRepository(db)
        self.group_member_repo = TournamentGroupMemberRepository(db)
        self.match_repo = MatchRepository(db)
        self.result_version_repo = MatchResultVersionRepository(db)
        self.standing_repo = GroupStandingRepository(db)
        self.bracket_repo = KnockoutBracketRepository(db)
        self.round_repo = KnockoutRoundRepository(db)
        self.slot_repo = KnockoutSlotRepository(db)
        self.schedule_version_repo = ScheduleVersionRepository(db)
        self.placement_repo = TournamentPlacementRepository(db)

    async def create_tournament(self, data: TournamentCreate, created_by: Optional[str] = None) -> Tournament:
        tournament = await self.tournament_repo.create(
            {
                "name": data.name,
                "description": data.description,
                "timezone": data.timezone,
                "status": TournamentStatus.DRAFT,
                "created_by": created_by,
                "group_config_json": json.dumps(
                    {
                        "group_count": data.group_count,
                        "teams_per_group": data.teams_per_group,
                        "qualification_count": data.qualification_count,
                        "tie_breaker": data.tie_breaker,
                    }
                ),
                "knockout_config_json": json.dumps(
                    {
                        "brackets": data.knockout_brackets,
                        "upper_loser_rule": data.upper_loser_rule,
                        "middle_loser_rule": data.middle_loser_rule,
                    }
                ),
                "third_place_mode": data.third_place_mode.value,
                "config_json": json.dumps(
                    {
                        "bo_formats": data.bo_formats,
                        "match_duration_minutes": data.match_duration_minutes,
                        "buffer_minutes": data.buffer_minutes,
                        "min_rest_minutes": data.min_rest_minutes,
                    }
                ),
            }
        )
        for d in data.dates:
            await self.date_repo.create(
                {
                    "tournament_id": tournament.id,
                    "date": d.date,
                    "start_time": d.start_time,
                    "end_time": d.end_time,
                    "match_duration_minutes": d.match_duration_minutes,
                    "buffer_minutes": d.buffer_minutes,
                    "min_rest_minutes": d.min_rest_minutes,
                }
            )
        return tournament

    async def get_tournament(self, tournament_id: str) -> Optional[Dict[str, Any]]:
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            return None
        dates = await self.date_repo.get_by_tournament(tournament_id)
        teams = await self.team_repo.get_by_tournament(tournament_id)
        groups = await self.group_repo.get_by_tournament(tournament_id)
        matches = await self.match_repo.get_by_tournament(tournament_id)
        brackets = await self.bracket_repo.get_by_tournament(tournament_id)
        placements = await self.placement_repo.get_by_tournament(tournament_id)
        schedule_versions = await self.schedule_version_repo.get_by_tournament(tournament_id)
        return {
            "tournament": tournament,
            "dates": dates,
            "teams": teams,
            "groups": groups,
            "matches": matches,
            "brackets": brackets,
            "placements": placements,
            "schedule_versions": schedule_versions,
        }

    async def list_tournaments(self) -> List[Tournament]:
        return await self.tournament_repo.get_all()

    async def update_tournament(self, tournament_id: str, data: TournamentUpdate) -> Optional[Tournament]:
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            return None
        if data.status and not can_transition(tournament.status, data.status.value):
            raise ValueError(f"Invalid transition from {tournament.status} to {data.status.value}")
        update_dict = data.model_dump(exclude_none=True)
        return await self.tournament_repo.update(tournament_id, update_dict)

    async def delete_tournament(self, tournament_id: str) -> bool:
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            return False
        if tournament.status not in [TournamentStatus.DRAFT, TournamentStatus.CANCELLED]:
            raise ValueError("Only DRAFT or CANCELLED tournaments can be deleted")
        return await self.tournament_repo.delete(tournament_id)

    async def select_teams(self, tournament_id: str, data: TournamentTeamSelect) -> Tournament:
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")
        if not can_transition(tournament.status, TournamentStatus.TEAMS_LOCKED):
            raise ValueError(f"Cannot select teams in status {tournament.status}")
        await self.team_repo.delete_by_tournament(tournament_id)
        for idx, team_id in enumerate(data.team_ids):
            await self.team_repo.create(
                {
                    "tournament_id": tournament_id,
                    "team_version_id": data.team_version_id,
                    "team_id": team_id,
                    "seed": idx + 1,
                }
            )
        tournament.selected_team_version_id = data.team_version_id
        tournament.status = TournamentStatus.TEAMS_LOCKED
        tournament.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(tournament)
        return tournament

    async def create_groups(self, tournament_id: str, data: TournamentGroupCreate) -> TournamentGroup:
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")
        if not can_transition(tournament.status, TournamentStatus.GROUPS_CONFIGURED):
            raise ValueError(f"Cannot create groups in status {tournament.status}")
        group = await self.group_repo.create(
            {
                "tournament_id": tournament_id,
                "name": data.name,
                "sort_order": data.sort_order,
            }
        )
        for idx, team_id in enumerate(data.team_ids):
            tournament_team = await self.team_repo.get_by_tournament_and_team(tournament_id, team_id)
            if not tournament_team:
                raise ValueError(f"Team {team_id} not in tournament")
            await self.group_member_repo.create(
                {
                    "group_id": group.id,
                    "tournament_team_id": tournament_team.id,
                    "seed": idx + 1,
                }
            )
        if tournament.status != TournamentStatus.GROUPS_CONFIGURED:
            tournament.status = TournamentStatus.GROUPS_CONFIGURED
            tournament.updated_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(tournament)
        return group

    async def update_group(self, group_id: str, data: TournamentGroupUpdate) -> Optional[TournamentGroup]:
        group = await self.group_repo.get_by_id(group_id)
        if not group:
            return None
        tournament = await self.tournament_repo.get_by_id(group.tournament_id)
        if tournament and tournament.status not in [
            TournamentStatus.GROUPS_CONFIGURED,
            TournamentStatus.SCHEDULE_GENERATED,
            TournamentStatus.GROUP_STAGE,
        ]:
            raise ValueError(f"Cannot update groups in status {tournament.status}")
        if data.name is not None:
            group.name = data.name
        if data.sort_order is not None:
            group.sort_order = data.sort_order
        if data.team_ids is not None:
            await self.group_member_repo.delete_by_group(group_id)
            for idx, team_id in enumerate(data.team_ids):
                tournament_team = await self.team_repo.get_by_tournament_and_team(group.tournament_id, team_id)
                if not tournament_team:
                    raise ValueError(f"Team {team_id} not in tournament")
                await self.group_member_repo.create(
                    {
                        "group_id": group_id,
                        "tournament_team_id": tournament_team.id,
                        "seed": idx + 1,
                    }
                )
        await self.db.flush()
        await self.db.refresh(group)
        return group

    async def clear_groups(self, tournament_id: str) -> None:
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")
        await self.group_repo.delete_by_tournament(tournament_id)
        await self.db.flush()
        if tournament.status == TournamentStatus.GROUPS_CONFIGURED:
            tournament.status = TournamentStatus.TEAMS_LOCKED
            tournament.updated_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(tournament)

    async def create_match(self, tournament_id: str, data: MatchCreate) -> Match:
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")
        if data.team_a_id and data.team_b_id and data.team_a_id == data.team_b_id:
            raise ValueError("Team A and Team B must be different")
        match = await self.match_repo.create(
            {
                "tournament_id": tournament_id,
                "stage": data.stage.value,
                "group_id": data.group_id,
                "bracket_id": data.bracket_id,
                "round": data.round,
                "match_number": data.match_number,
                "scheduled_date": data.scheduled_date,
                "start_time": data.start_time,
                "end_time": data.end_time,
                "team_a_id": data.team_a_id,
                "team_b_id": data.team_b_id,
                "format": data.format.value,
                "status": MatchStatus.SCHEDULED,
            }
        )
        return match

    async def update_match(self, tournament_id: str, match_id: str, data: MatchUpdate) -> Optional[Match]:
        match = await self.match_repo.get_by_id(match_id)
        if not match:
            return None
        if match.tournament_id != tournament_id:
            raise ValueError("Match does not belong to this tournament")
        if match.status in [MatchStatus.ONGOING, MatchStatus.COMPLETED]:
            raise ValueError(f"Cannot update match in status {match.status}")
        if data.team_a_id and data.team_b_id and data.team_a_id == data.team_b_id:
            raise ValueError("Team A and Team B must be different")
        update_dict = data.model_dump(exclude_none=True)
        return await self.match_repo.update(match_id, update_dict)

    async def delete_match(self, tournament_id: str, match_id: str) -> bool:
        match = await self.match_repo.get_by_id(match_id)
        if not match:
            return False
        if match.tournament_id != tournament_id:
            raise ValueError("Match does not belong to this tournament")
        if match.status == MatchStatus.COMPLETED:
            raise ValueError("Cannot delete completed match")
        return await self.match_repo.delete(match_id)

    async def submit_match_result(self, tournament_id: str, match_id: str, data: MatchResultSubmit) -> Optional[Match]:
        match = await self.match_repo.get_by_id(match_id)
        if not match:
            raise ValueError("Match not found")
        if match.tournament_id != tournament_id:
            raise ValueError("Match does not belong to this tournament")
        if match.status == MatchStatus.COMPLETED:
            raise ValueError("Match already completed")
        required_wins = BO_WIN_REQUIREMENTS.get(match.format)
        if required_wins is None:
            raise ValueError(f"Unknown format: {match.format}")
        if data.score_a != required_wins and data.score_b != required_wins:
            raise ValueError(f"Invalid score for {match.format}: winner must have exactly {required_wins} wins")
        if data.score_a == data.score_b:
            raise ValueError("Score cannot be tied")
        winner_id = match.team_a_id if data.score_a > data.score_b else match.team_b_id
        match.score_a = data.score_a
        match.score_b = data.score_b
        match.kills_a = data.kills_a
        match.kills_b = data.kills_b
        match.deaths_a = data.deaths_a
        match.deaths_b = data.deaths_b
        match.winner_team_id = winner_id
        match.status = MatchStatus.COMPLETED
        match.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(match)
        next_version = await self.result_version_repo.get_next_version(match_id)
        await self.result_version_repo.create(
            {
                "match_id": match_id,
                "version": next_version,
                "score_a": data.score_a,
                "score_b": data.score_b,
                "kills_a": data.kills_a,
                "kills_b": data.kills_b,
                "deaths_a": data.deaths_a,
                "deaths_b": data.deaths_b,
                "winner_team_id": winner_id,
                "verified": True,
                "change_reason": data.change_reason,
            }
        )
        await self.db.flush()
        return match

    async def confirm_match_result(self, tournament_id: str, match_id: str) -> Optional[Match]:
        match = await self.match_repo.get_by_id(match_id)
        if not match:
            raise ValueError("Match not found")
        if match.tournament_id != tournament_id:
            raise ValueError("Match does not belong to this tournament")
        if not match.winner_team_id:
            raise ValueError("Match has no result to confirm")
        if match.stage == MatchStage.GROUP_STAGE:
            await self._recalculate_group_standings(tournament_id, match.group_id)
        await self.db.flush()
        return match

    async def _recalculate_group_standings(self, tournament_id: str, group_id: str):
        group = await self.group_repo.get_by_id(group_id)
        if not group:
            return
        members = await self.group_member_repo.get_by_group(group_id)
        await self.standing_repo.delete_by_group(group_id)
        for member in members:
            team_id = member.tournament_team.team_id if member.tournament_team else None
            if not team_id:
                continue
            matches = await self.match_repo.get_by_tournament(tournament_id, MatchStage.GROUP_STAGE)
            team_matches = [m for m in matches if (m.team_a_id == team_id or m.team_b_id == team_id) and m.group_id == group_id and m.status == MatchStatus.COMPLETED]
            played = len(team_matches)
            win = 0
            loss = 0
            kill = 0
            death = 0
            for m in team_matches:
                if m.team_a_id == team_id:
                    kill += m.kills_a or 0
                    death += m.deaths_a or 0
                    if m.winner_team_id == team_id:
                        win += 1
                    else:
                        loss += 1
                elif m.team_b_id == team_id:
                    kill += m.kills_b or 0
                    death += m.deaths_b or 0
                    if m.winner_team_id == team_id:
                        win += 1
                    else:
                        loss += 1
            kill_difference = kill - death
            points = win * 2
            await self.standing_repo.create_or_update(
                {
                    "group_id": group_id,
                    "team_id": team_id,
                    "played": played,
                    "win": win,
                    "loss": loss,
                    "kill": kill,
                    "death": death,
                    "kill_difference": kill_difference,
                    "points": points,
                }
            )

    async def override_standings(self, tournament_id: str, group_id: str, data: List[StandingsOverride], actor: Optional[str] = None) -> List[GroupStanding]:
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")
        results = []
        for item in data:
            standing = await self.standing_repo.get_by_group_and_team(group_id, item.team_id)
            if not standing:
                standing = GroupStanding(group_id=group_id, team_id=item.team_id)
                self.db.add(standing)
                await self.db.flush()
            update_fields = item.model_dump(exclude_none=True)
            update_fields.pop("reason", None)
            for key, value in update_fields.items():
                if hasattr(standing, key):
                    setattr(standing, key, value)
            standing.is_manual_override = True
            standing.computed_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(standing)
            results.append(standing)
        return results

    async def finalize_group_stage(self, tournament_id: str) -> Tournament:
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")
        if not can_transition(tournament.status, TournamentStatus.GROUP_FINALIZED):
            raise ValueError(f"Cannot finalize group stage in status {tournament.status}")
        groups = await self.group_repo.get_by_tournament(tournament_id)
        for group in groups:
            standings = await self.standing_repo.get_by_group(group.id)
            if not standings:
                raise ValueError(f"Group {group.name} has no standings")
            for s in standings:
                if s.played == 0:
                    raise ValueError(f"Group {group.name} has teams with no matches played")
        tournament.status = TournamentStatus.GROUP_FINALIZED
        tournament.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(tournament)
        return tournament

    async def reopen_group_stage(self, tournament_id: str) -> Tournament:
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")
        if not can_transition(tournament.status, TournamentStatus.GROUP_STAGE):
            raise ValueError(f"Cannot reopen group stage in status {tournament.status}")
        tournament.status = TournamentStatus.GROUP_STAGE
        tournament.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(tournament)
        return tournament

    async def set_placement(self, tournament_id: str, data: PlacementSet) -> TournamentPlacement:
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")
        existing = await self.placement_repo.get_by_tournament_and_team(tournament_id, data.team_id)
        if existing:
            for key, value in data.model_dump(exclude_none=True).items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        placement = await self.placement_repo.create(
            {
                "tournament_id": tournament_id,
                "team_id": data.team_id,
                "placement": data.placement,
                "source": data.source,
            }
        )
        return placement

    async def finalize_champion(self, tournament_id: str) -> Tournament:
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")
        placements = await self.placement_repo.get_by_tournament(tournament_id)
        for p in placements:
            if p.placement == 1:
                tournament.champion_team_id = p.team_id
            elif p.placement == 2:
                tournament.runner_up_team_id = p.team_id
            elif p.placement == 3:
                tournament.third_place_team_id = p.team_id
        tournament.status = TournamentStatus.COMPLETED
        tournament.finalized_at = datetime.utcnow()
        tournament.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(tournament)
        return tournament

    async def get_matches_for_schedule(self, tournament_id: str) -> List[Match]:
        return await self.match_repo.get_by_tournament(tournament_id)

    async def save_schedule_version(self, tournament_id: str, created_by: Optional[str] = None, notes: Optional[str] = None) -> ScheduleVersion:
        existing = await self.schedule_version_repo.get_by_tournament(tournament_id)
        next_version = len(existing) + 1
        return await self.schedule_version_repo.create(
            {
                "tournament_id": tournament_id,
                "version": next_version,
                "created_by": created_by,
                "notes": notes,
            }
        )
