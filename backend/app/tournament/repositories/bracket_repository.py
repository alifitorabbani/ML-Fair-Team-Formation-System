from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List

from app.tournament.models.tournament_models import KnockoutBracket

class KnockoutBracketRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> KnockoutBracket:
        bracket = KnockoutBracket(**data)
        self.db.add(bracket)
        await self.db.flush()
        await self.db.refresh(bracket)
        return bracket

    async def get_by_tournament(self, tournament_id: str) -> List[KnockoutBracket]:
        result = await self.db.execute(
            select(KnockoutBracket)
            .where(KnockoutBracket.tournament_id == tournament_id)
            .order_by(KnockoutBracket.sort_order)
        )
        return list(result.scalars().all())

    async def delete_by_tournament(self, tournament_id: str):
        await self.db.execute(delete(KnockoutBracket).where(KnockoutBracket.tournament_id == tournament_id))
