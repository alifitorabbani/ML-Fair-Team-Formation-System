from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.tournament.models.tournament_models import Match, GroupStanding, TournamentGroup, TournamentGroupMember, DailyStanding
from app.tournament.repositories import MatchRepository, GroupStandingRepository, TournamentGroupRepository, TournamentGroupMemberRepository, DailyStandingRepository
from app.tournament.constants import MatchStatus


class StandingsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.match_repo = MatchRepository(db)
        self.standing_repo = GroupStandingRepository(db)
        self.group_repo = TournamentGroupRepository(db)
        self.group_member_repo = TournamentGroupMemberRepository(db)
        self.daily_standing_repo = DailyStandingRepository(db)

    async def recalculate_group_standings(self, tournament_id: str, group_id: str) -> List[Dict[str, Any]]:
        group = await self.group_repo.get_by_id(group_id)
        if not group:
            raise ValueError("Group not found")
        members = await self.group_member_repo.get_by_group(group_id)
        matches = await self.match_repo.get_by_tournament(tournament_id)
        group_matches = [m for m in matches if m.group_id == group_id and m.stage == "GROUP_STAGE" and m.status == MatchStatus.COMPLETED]
        computed = []
        for member in members:
            team_id = member.tournament_team.team_id if member.tournament_team else None
            if not team_id:
                continue
            team_matches = [m for m in group_matches if m.team_a_id == team_id or m.team_b_id == team_id]
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
            win_rate = (win / played) * 100 if played > 0 else 0.0
            standing = await self.standing_repo.create_or_update(
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
            computed.append(
                {
                    "team_id": team_id,
                    "played": standing.played,
                    "win": standing.win,
                    "loss": standing.loss,
                    "kill": standing.kill,
                    "death": standing.death,
                    "kill_difference": standing.kill_difference,
                    "points": standing.points,
                    "win_rate": win_rate,
                    "rank": standing.rank,
                }
            )
        computed.sort(key=lambda x: (-x["points"], -x["win"], -x["kill_difference"], -x["kill"], x["death"]))
        for idx, item in enumerate(computed):
            standing = await self.standing_repo.get_by_group_and_team(group_id, item["team_id"])
            if standing:
                standing.rank = idx + 1
                await self.db.flush()
                item["rank"] = idx + 1
        return computed

    async def get_standings(self, group_id: str) -> List[Dict[str, Any]]:
        group = await self.group_repo.get_by_id(group_id)
        if not group:
            raise ValueError("Group not found")
        members = await self.group_member_repo.get_by_group(group_id)
        standings = await self.standing_repo.get_by_group(group_id)
        standings_map = {s.team_id: s for s in standings}
        results = []
        for member in members:
            team_id = member.tournament_team.team_id if member.tournament_team else None
            standing = standings_map.get(team_id)
            if not standing:
                continue
            results.append(
                {
                    "team_id": team_id,
                    "team_name": member.tournament_team.team_name_snapshot if member.tournament_team else None,
                    "rank": standing.rank,
                    "played": standing.played,
                    "win": standing.win,
                    "loss": standing.loss,
                    "kill": standing.kill,
                    "death": standing.death,
                    "kill_difference": standing.kill_difference,
                    "points": standing.points,
                    "win_rate": (standing.win / standing.played) * 100 if standing.played > 0 else 0.0,
                    "is_manual_override": standing.is_manual_override,
                }
            )
        results.sort(key=lambda x: (x["rank"] or 999))
        return results

    async def recalculate_daily_standings(self, tournament_id: str, group_id: str, match_date: str) -> List[Dict[str, Any]]:
        group = await self.group_repo.get_by_id(group_id)
        if not group:
            raise ValueError("Group not found")
        members = await self.group_member_repo.get_by_group(group_id)
        matches = await self.match_repo.get_by_tournament(tournament_id)
        group_matches = [
            m for m in matches
            if m.group_id == group_id and m.stage == "GROUP_STAGE" and m.status == MatchStatus.COMPLETED
            and m.scheduled_date is not None and m.scheduled_date.isoformat() == match_date
        ]
        computed = []
        for member in members:
            team_id = member.tournament_team.team_id if member.tournament_team else None
            if not team_id:
                continue
            team_matches = [m for m in group_matches if m.team_a_id == team_id or m.team_b_id == team_id]
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
            await self.daily_standing_repo.create_or_update(
                {
                    "tournament_id": tournament_id,
                    "group_id": group_id,
                    "team_id": team_id,
                    "match_date": match_date,
                    "played": played,
                    "win": win,
                    "loss": loss,
                    "kill": kill,
                    "death": death,
                    "kill_difference": kill_difference,
                    "points": points,
                }
            )
            computed.append(
                {
                    "team_id": team_id,
                    "team_name": member.tournament_team.team_name_snapshot if member.tournament_team else None,
                    "played": played,
                    "win": win,
                    "loss": loss,
                    "kill": kill,
                    "death": death,
                    "kill_difference": kill_difference,
                    "points": points,
                    "match_date": match_date,
                }
            )
        computed.sort(key=lambda x: (-x["points"], -x["kill_difference"], -x["kill"]))
        return computed

    async def get_daily_standings(self, tournament_id: str, match_date: str) -> List[Dict[str, Any]]:
        standings = await self.daily_standing_repo.get_by_tournament_and_date(tournament_id, match_date)
        results = []
        for s in standings:
            results.append(
                {
                    "team_id": s.team_id,
                    "team_name": None,
                    "played": s.played,
                    "win": s.win,
                    "loss": s.loss,
                    "kill": s.kill,
                    "death": s.death,
                    "kill_difference": s.kill_difference,
                    "points": s.points,
                    "match_date": s.match_date.isoformat() if s.match_date else None,
                }
            )
        results.sort(key=lambda x: (-x["points"], -x["kill_difference"], -x["kill"]))
        return results
