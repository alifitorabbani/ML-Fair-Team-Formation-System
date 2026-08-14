from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.models.models import ParticipantDB
from app.schemas.schemas import ParticipantFeatures, ParticipantStatus


class ParticipantRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> List[ParticipantDB]:
        result = await self.db.execute(select(ParticipantDB).order_by(ParticipantDB.id))
        return list(result.scalars().all())

    async def get_by_id(self, player_id: str) -> Optional[ParticipantDB]:
        result = await self.db.execute(select(ParticipantDB).where(ParticipantDB.id == player_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[ParticipantDB]:
        result = await self.db.execute(select(ParticipantDB).where(ParticipantDB.email == email))
        return result.scalar_one_or_none()

    async def count(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(ParticipantDB))
        return result.scalar_one() or 0

    async def upsert_many(self, participants: List[dict]) -> int:
        from sqlalchemy.dialects.sqlite import insert
        from uuid import uuid4

        count = 0
        for p in participants:
            existing = await self.get_by_id(p["id"])
            if existing:
                for key, value in p.items():
                    if key != "id":
                        setattr(existing, key, value)
                count += 1
            else:
                db_p = ParticipantDB(**p)
                self.db.add(db_p)
                count += 1
        await self.db.flush()
        return count

    async def clear_all(self) -> None:
        result = await self.db.execute(select(ParticipantDB))
        participants = result.scalars().all()
        for p in participants:
            await self.db.delete(p)
        await self.db.flush()

    async def update_status(self, player_id: str, status: str) -> None:
        participant = await self.get_by_id(player_id)
        if participant:
            participant.status = status
            await self.db.flush()

    async def update_rank(self, player_id: str, rank: Optional[int]) -> None:
        participant = await self.get_by_id(player_id)
        if participant:
            participant.rank = rank
            await self.db.flush()
