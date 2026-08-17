from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List

from app.tournament.models.tournament_models import KnockoutRound

class KnockoutRoundRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> KnockoutRound:
        round_obj = KnockoutRound(**data)
        self.db.add(round_obj)
        await self.db.flush()
        await self.db.refresh(round_obj)
        return round_obj

    async def get_by_bracket(self, bracket_id: str) -> List[KnockoutRound]:
        result = await self.db.execute(
            select(KnockoutRound).where(KnockoutRound.bracket_id == bracket_id).order_by(KnockoutRound.round_number)
        )
        return list(result.scalars().all())

    async def get_by_id(self, round_id: str) -> Optional[KnockoutRound]:
        result = await self.db.execute(select(KnockoutRound).where(KnockoutRound.id == round_id))
        return result.scalar_one_or_none()
