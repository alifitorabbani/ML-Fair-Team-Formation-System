from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, func
from typing import Optional, List, Any
from datetime import datetime

from app.tournament.models.tournament_models import Tournament

class TournamentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> Tournament:
        tournament = Tournament(**data)
        self.db.add(tournament)
        await self.db.flush()
        await self.db.refresh(tournament)
        return tournament

    async def get_by_id(self, tournament_id: str) -> Optional[Tournament]:
        result = await self.db.execute(select(Tournament).where(Tournament.id == tournament_id))
        return result.scalar_one_or_none()

    async def get_all(self) -> List[Tournament]:
        result = await self.db.execute(select(Tournament).order_by(Tournament.created_at.desc()))
        return list(result.scalars().all())

    async def update(self, tournament_id: str, data: dict) -> Optional[Tournament]:
        tournament = await self.get_by_id(tournament_id)
        if not tournament:
            return None
        for key, value in data.items():
            if hasattr(tournament, key):
                setattr(tournament, key, value)
        tournament.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(tournament)
        return tournament

    async def delete(self, tournament_id: str) -> bool:
        tournament = await self.get_by_id(tournament_id)
        if not tournament:
            return False
        await self.db.delete(tournament)
        await self.db.flush()
        return True
