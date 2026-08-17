from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List

from app.tournament.models.tournament_models import KnockoutSlot

class KnockoutSlotRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> KnockoutSlot:
        slot = KnockoutSlot(**data)
        self.db.add(slot)
        await self.db.flush()
        await self.db.refresh(slot)
        return slot

    async def get_by_round(self, round_id: str) -> List[KnockoutSlot]:
        result = await self.db.execute(
            select(KnockoutSlot).where(KnockoutSlot.round_id == round_id).order_by(KnockoutSlot.slot_number)
        )
        return list(result.scalars().all())

    async def update(self, slot_id: str, data: dict) -> Optional[KnockoutSlot]:
        result = await self.db.execute(select(KnockoutSlot).where(KnockoutSlot.id == slot_id))
        slot = result.scalar_one_or_none()
        if not slot:
            return None
        for key, value in data.items():
            if hasattr(slot, key):
                setattr(slot, key, value)
        await self.db.flush()
        await self.db.refresh(slot)
        return slot
