from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.tournament.models.tournament_models import (
    TournamentGroup,
    TournamentGroupMember,
    TournamentTeam,
    Match,
    GroupStanding,
)
from app.tournament.repositories import (
    TournamentRepository,
    TournamentGroupRepository,
    TournamentGroupMemberRepository,
    TournamentTeamRepository,
    MatchRepository,
    GroupStandingRepository,
)
from app.tournament.constants import MatchStatus, MatchStage
from app.tournament.services.standings_service import StandingsService


class GroupService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tournament_repo = TournamentRepository(db)
        self.group_repo = TournamentGroupRepository(db)
        self.group_member_repo = TournamentGroupMemberRepository(db)
        self.team_repo = TournamentTeamRepository(db)
        self.match_repo = MatchRepository(db)
        self.standing_repo = GroupStandingRepository(db)
        self.standings_service = StandingsService(db)

    async def create_group(self, tournament_id: str, name: str, team_ids: List[str], sort_order: Optional[int] = None) -> TournamentGroup:
        group = await self.group_repo.create(
            {
                "tournament_id": tournament_id,
                "name": name,
                "sort_order": sort_order,
            }
        )
        for idx, team_id in enumerate(team_ids):
            tournament_team = await self.team_repo.get_by_tournament_and_team(tournament_id, team_id)
            if not tournament_team:
                raise ValueError(f"Team {team_id} not found in tournament")
            await self.group_member_repo.create(
                {
                    "group_id": group.id,
                    "tournament_team_id": tournament_team.id,
                    "seed": idx + 1,
                }
            )
        return group

    async def get_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        group = await self.group_repo.get_by_id(group_id)
        if not group:
            return None
        members = await self.group_member_repo.get_by_group(group_id)
        standings = await self.standing_repo.get_by_group(group_id)
        return {
            "group": group,
            "members": members,
            "standings": standings,
        }

    async def list_groups(self, tournament_id: str) -> List[TournamentGroup]:
        return await self.group_repo.get_by_tournament(tournament_id)

    async def update_group(self, group_id: str, name: Optional[str] = None, team_ids: Optional[List[str]] = None, sort_order: Optional[int] = None) -> Optional[TournamentGroup]:
        group = await self.group_repo.get_by_id(group_id)
        if not group:
            return None
        if name is not None:
            group.name = name
        if sort_order is not None:
            group.sort_order = sort_order
        if team_ids is not None:
            await self.group_member_repo.delete_by_group(group_id)
            for idx, team_id in enumerate(team_ids):
                tournament_team = await self.team_repo.get_by_tournament_and_team(group.tournament_id, team_id)
                if not tournament_team:
                    raise ValueError(f"Team {team_id} not found in tournament")
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

    async def get_group_standings(self, group_id: str) -> List[Dict[str, Any]]:
        group = await self.group_repo.get_by_id(group_id)
        if not group:
            raise ValueError("Group not found")
        members = await self.group_member_repo.get_by_group(group_id)
        standings_raw = await self.standing_repo.get_by_group(group_id)
        standings_map = {s.team_id: s for s in standings_raw}
        results = []
        for member in members:
            team_id = member.tournament_team.team_id if member.tournament_team else None
            standing = standings_map.get(team_id, None)
            results.append(
                {
                    "team_id": team_id,
                    "team_name": member.tournament_team.team_name_snapshot if member.tournament_team else None,
                    "seed": member.seed,
                    "rank": standing.rank if standing else None,
                    "played": standing.played if standing else 0,
                    "win": standing.win if standing else 0,
                    "loss": standing.loss if standing else 0,
                    "kill": standing.kill if standing else 0,
                    "death": standing.death if standing else 0,
                    "kill_difference": standing.kill_difference if standing else 0,
                    "points": standing.points if standing else 0,
                    "is_manual_override": standing.is_manual_override if standing else False,
                }
            )
        return results

    async def recalculate_group_standings(self, tournament_id: str, group_id: str) -> List[Dict[str, Any]]:
        return await self.standings_service.recalculate_group_standings(tournament_id, group_id)
