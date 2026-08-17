from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List

from app.tournament.models.tournament_models import BracketStanding


class BracketStandingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_or_update(self, data: dict) -> BracketStanding:
        tournament_id = data["tournament_id"]
        team_id = data["team_id"]
        existing = await self.get_by_tournament_and_team(tournament_id, team_id)
        if existing:
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.computed_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        standing = BracketStanding(**data)
        self.db.add(standing)
        await self.db.flush()
        await self.db.refresh(standing)
        return standing

    async def get_by_tournament_and_team(self, tournament_id: str, team_id: str) -> Optional[BracketStanding]:
        result = await self.db.execute(
            select(BracketStanding).where(BracketStanding.tournament_id == tournament_id, BracketStanding.team_id == team_id)
        )
        return result.scalar_one_or_none()

    async def get_by_tournament(self, tournament_id: str) -> List[BracketStanding]:
        result = await self.db.execute(
            select(BracketStanding)
            .where(BracketStanding.tournament_id == tournament_id)
            .order_by(BracketStanding.points.desc(), BracketStanding.wins.desc())
        )
        return list(result.scalars().all())

    async def delete_by_tournament(self, tournament_id: str):
        await self.db.execute(delete(BracketStanding).where(BracketStanding.tournament_id == tournament_id))
