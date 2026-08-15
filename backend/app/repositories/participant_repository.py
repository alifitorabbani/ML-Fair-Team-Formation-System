from typing import List, Optional, Dict
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

    async def get_by_ids(self, ids: List[str]) -> List[ParticipantDB]:
        if not ids:
            return []
        result = await self.db.execute(
            select(ParticipantDB).where(ParticipantDB.id.in_(ids)).order_by(ParticipantDB.id)
        )
        return list(result.scalars().all())

    async def get_by_status(self, status: str) -> List[ParticipantDB]:
        result = await self.db.execute(
            select(ParticipantDB).where(ParticipantDB.status == status).order_by(ParticipantDB.id)
        )
        return list(result.scalars().all())

    async def get_ranked(self, page: int = 1, page_size: int = 20) -> List[ParticipantDB]:
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(ParticipantDB)
            .where(ParticipantDB.status == "QUALIFIED")
            .order_by(ParticipantDB.rank.asc())
            .limit(page_size)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_ranked(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(ParticipantDB).where(ParticipantDB.status == "QUALIFIED")
        )
        return result.scalar_one() or 0

    async def get_by_id(self, player_id: str) -> Optional[ParticipantDB]:
        result = await self.db.execute(select(ParticipantDB).where(ParticipantDB.id == player_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[ParticipantDB]:
        result = await self.db.execute(select(ParticipantDB).where(ParticipantDB.email == email))
        return result.scalar_one_or_none()

    async def count(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(ParticipantDB))
        return result.scalar_one() or 0

    async def count_by_status(self, status: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(ParticipantDB).where(ParticipantDB.status == status)
        )
        return result.scalar_one() or 0

    async def count_processed(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(ParticipantDB).where(ParticipantDB.skill_score.is_not(None))
        )
        return result.scalar_one() or 0

    async def upsert_many(self, participants: List[dict]) -> int:
        existing = await self.get_all()
        existing_map = {p.id: p for p in existing}

        new_participants = []
        updated_count = 0

        for p in participants:
            participant_id = p.get("id")
            if not participant_id:
                continue

            if participant_id in existing_map:
                existing_p = existing_map[participant_id]
                for key, value in p.items():
                    if key != "id":
                        setattr(existing_p, key, value)
                updated_count += 1
            else:
                new_participants.append(ParticipantDB(**p))

        if new_participants:
            self.db.add_all(new_participants)

        await self.db.flush()
        return updated_count + len(new_participants)

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

    async def bulk_update_status_and_rank(self, status_map: Dict[str, str], rank_map: Dict[str, int]) -> None:
        participants = await self.get_all()
        for p in participants:
            if p.id in status_map:
                p.status = status_map[p.id]
            if p.id in rank_map:
                p.rank = rank_map[p.id]
        await self.db.flush()
