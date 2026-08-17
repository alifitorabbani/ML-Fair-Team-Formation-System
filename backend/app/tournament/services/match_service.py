from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.tournament.models.tournament_models import Match, MatchResultVersion
from app.tournament.repositories import MatchRepository, MatchResultVersionRepository
from app.tournament.constants import BOFormat, BO_WIN_REQUIREMENTS, MatchStatus


class MatchService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.match_repo = MatchRepository(db)
        self.result_version_repo = MatchResultVersionRepository(db)

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

    async def submit_result(self, match_id: str, score_a: int, score_b: int, kills_a: Optional[int] = None, kills_b: Optional[int] = None, deaths_a: Optional[int] = None, deaths_b: Optional[int] = None, change_reason: Optional[str] = None) -> Match:
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
                    "winner_team_id": match.team_a_id if score_a > score_b else match.team_b_id,
                    "change_reason": change_reason,
                }
            )
        match.score_a = score_a
        match.score_b = score_b
        match.kills_a = kills_a
        match.kills_b = kills_b
        match.deaths_a = deaths_a
        match.deaths_b = deaths_b
        match.winner_team_id = match.team_a_id if score_a > score_b else match.team_b_id
        match.status = MatchStatus.COMPLETED
        match.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(match)
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
