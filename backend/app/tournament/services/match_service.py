from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.tournament.models.tournament_models import Match, MatchResultVersion, BracketMatchMap
from app.tournament.repositories import MatchRepository, MatchResultVersionRepository, BracketMatchMapRepository
from app.tournament.constants import BOFormat, BO_WIN_REQUIREMENTS, MatchStatus


class MatchService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.match_repo = MatchRepository(db)
        self.result_version_repo = MatchResultVersionRepository(db)
        self.map_repo = BracketMatchMapRepository(db)

    def validate_bo_score(self, score_a: int, score_b: int, format: str) -> bool:
        required = BO_WIN_REQUIREMENTS.get(format)
        if required is None:
            return False
        if score_a == score_b:
            return False
        if score_a != required and score_b != required:
            return False
        max_possible = required
        if score_a > max_possible or score_b > max_possible:
            return False
        return True

    async def submit_result(self, match_id: str, score_a: int, score_b: int, kills_a: Optional[int] = None, kills_b: Optional[int] = None, deaths_a: Optional[int] = None, deaths_b: Optional[int] = None, winner_team_id: Optional[str] = None, loser_team_id: Optional[str] = None, change_reason: Optional[str] = None, map_results: Optional[List[Dict[str, Any]]] = None) -> Match:
        match = await self.match_repo.get_by_id(match_id)
        if not match:
            raise ValueError("Match not found")
        if not self.validate_bo_score(score_a, score_b, match.format):
            raise ValueError(f"Invalid score {score_a}-{score_b} for format {match.format}")
        if match.status == MatchStatus.COMPLETED:
            next_version = await self.result_version_repo.get_next_version(match_id)
            await self.result_version_repo.create(
                {
                    "match_id": match_id,
                    "version": next_version,
                    "score_a": score_a,
                    "score_b": score_b,
                    "kills_a": kills_a,
                    "kills_b": kills_b,
                    "deaths_a": deaths_a,
                    "deaths_b": deaths_b,
                    "winner_team_id": winner_team_id or (match.team_a_id if score_a > score_b else match.team_b_id),
                    "change_reason": change_reason,
                }
            )
        # Admin-assigned winner/loser take precedence; fallback to score only if not provided
        final_winner = winner_team_id or (match.team_a_id if score_a > score_b else match.team_b_id)
        final_loser = loser_team_id or (match.team_b_id if score_a > score_b else match.team_a_id)
        if final_winner not in (match.team_a_id, match.team_b_id):
            raise ValueError("Winner must be one of the match participants")
        if final_loser not in (match.team_a_id, match.team_b_id):
            raise ValueError("Loser must be one of the match participants")
        if final_winner == final_loser:
            raise ValueError("Winner and loser must be different")
        match.score_a = score_a
        match.score_b = score_b
        match.kills_a = kills_a
        match.kills_b = kills_b
        match.deaths_a = deaths_a
        match.deaths_b = deaths_b
        match.winner_team_id = final_winner
        match.status = MatchStatus.COMPLETED
        match.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(match)
        if map_results and match.format in (BOFormat.BO3, BOFormat.BO5, BOFormat.BO7):
            await self.map_repo.delete_by_match(match_id)
            required_wins = BO_WIN_REQUIREMENTS.get(match.format, 1)
            team_a_wins = 0
            team_b_wins = 0
            for map_data in map_results:
                map_number = map_data.get("map_number")
                if map_number is None:
                    continue
                map_winner = map_data.get("winner_team_id")
                if map_winner == match.team_a_id:
                    team_a_wins += 1
                elif map_winner == match.team_b_id:
                    team_b_wins += 1
                await self.map_repo.create(
                    {
                        "match_id": match_id,
                        "map_number": map_number,
                        "team_a_id": map_data.get("team_a_id", match.team_a_id),
                        "team_b_id": map_data.get("team_b_id", match.team_b_id),
                        "winner_team_id": map_winner,
                        "score_a": map_data.get("score_a"),
                        "score_b": map_data.get("score_b"),
                        "kills_a": map_data.get("kills_a"),
                        "kills_b": map_data.get("kills_b"),
                        "deaths_a": map_data.get("deaths_a"),
                        "deaths_b": map_data.get("deaths_b"),
                        "status": "COMPLETED",
                    }
                )
                if team_a_wins >= required_wins or team_b_wins >= required_wins:
                    break
        next_version = await self.result_version_repo.get_next_version(match_id)
        await self.result_version_repo.create(
            {
                "match_id": match_id,
                "version": next_version,
                "score_a": score_a,
                "score_b": score_b,
                "kills_a": kills_a,
                "kills_b": kills_b,
                "deaths_a": deaths_a,
                "deaths_b": deaths_b,
                "winner_team_id": match.winner_team_id,
                "verified": True,
                "change_reason": change_reason,
            }
        )
        await self.db.flush()
        return match

    async def confirm_result(self, match_id: str) -> Match:
        match = await self.match_repo.get_by_id(match_id)
        if not match:
            raise ValueError("Match not found")
        if not match.winner_team_id:
            raise ValueError("Match has no result to confirm")
        latest_version = await self.result_version_repo.get_latest_by_match(match_id)
        if latest_version and not latest_version.verified:
            latest_version.verified = True
            await self.db.flush()
        return match

    async def get_result_history(self, match_id: str) -> List[MatchResultVersion]:
        return await self.result_version_repo.get_by_match(match_id)
    async def submit_game_result(self, match_id: str, game_number: int, data: Dict[str, Any]) -> BracketMatchMap:
        match = await self.match_repo.get_by_id(match_id)
        if not match:
            raise ValueError("Match not found")
        if match.format not in (BOFormat.BO3, BOFormat.BO5, BOFormat.BO7):
            raise ValueError("Game results only supported for BO3/BO5/BO7 matches")
        
        # Check if game result already exists
        existing = await self.map_repo.get_by_match_and_number(match_id, game_number)
        if existing:
            # Update existing game result
            updated = await self.map_repo.update(existing.id, {
                "team_a_id": data.get("team_a_id", existing.team_a_id),
                "team_b_id": data.get("team_b_id", existing.team_b_id),
                "winner_team_id": data.get("winner_team_id"),
                "score_a": data.get("score_a"),
                "score_b": data.get("score_b"),
                "kills_a": data.get("kills_a"),
                "kills_b": data.get("kills_b"),
                "deaths_a": data.get("deaths_a"),
                "deaths_b": data.get("deaths_b"),
                "scheduled_date": data.get("scheduled_date"),
                "start_time": data.get("start_time"),
                "end_time": data.get("end_time"),
                "status": "COMPLETED",
            })
            return updated
        else:
            # Create new game result
            created = await self.map_repo.create({
                "match_id": match_id,
                "map_number": game_number,
                "team_a_id": data.get("team_a_id", match.team_a_id),
                "team_b_id": data.get("team_b_id", match.team_b_id),
                "winner_team_id": data.get("winner_team_id"),
                "score_a": data.get("score_a"),
                "score_b": data.get("score_b"),
                "kills_a": data.get("kills_a"),
                "kills_b": data.get("kills_b"),
                "deaths_a": data.get("deaths_a"),
                "deaths_b": data.get("deaths_b"),
                "scheduled_date": data.get("scheduled_date"),
                "start_time": data.get("start_time"),
                "end_time": data.get("end_time"),
                "status": "COMPLETED",
            })
            return created

