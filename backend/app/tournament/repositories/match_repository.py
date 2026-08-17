from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime
from typing import Optional, List

from app.tournament.models.tournament_models import Match

class MatchRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> Match:
        match = Match(**data)
        self.db.add(match)
        await self.db.flush()
        await self.db.refresh(match)
        return match

    async def get_by_id(self, match_id: str) -> Optional[Match]:
        result = await self.db.execute(select(Match).where(Match.id == match_id))
        return result.scalar_one_or_none()

    async def get_by_tournament(self, tournament_id: str, stage: Optional[str] = None) -> List[Match]:
        query = select(Match).where(Match.tournament_id == tournament_id)
        if stage:
            query = query.where(Match.stage == stage)
        # Use coalesce for nullable date/time columns so ordering is stable
        query = query.order_by(
            Match.scheduled_date.is_(None),
            Match.scheduled_date,
            Match.start_time,
            Match.match_number,
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(self, match_id: str, data: dict) -> Optional[Match]:
        match = await self.get_by_id(match_id)
        if not match:
            return None
        for key, value in data.items():
            if hasattr(match, key):
                setattr(match, key, value)
        match.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(match)
        return match

    async def delete(self, match_id: str) -> bool:
        match = await self.get_by_id(match_id)
        if not match:
            return False
        await self.db.delete(match)
        await self.db.flush()
        return True

    async def delete_by_tournament(self, tournament_id: str):
        await self.db.execute(delete(Match).where(Match.tournament_id == tournament_id))
