from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List

from app.tournament.models.tournament_models import BracketMatchMap


class BracketMatchMapRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> BracketMatchMap:
        map_result = BracketMatchMap(**data)
        self.db.add(map_result)
        await self.db.flush()
        await self.db.refresh(map_result)
        return map_result

    async def get_by_match(self, match_id: str) -> List[BracketMatchMap]:
        result = await self.db.execute(
            select(BracketMatchMap).where(BracketMatchMap.match_id == match_id).order_by(BracketMatchMap.map_number)
        )
        return list(result.scalars().all())

    async def get_by_match_and_number(self, match_id: str, map_number: int) -> Optional[BracketMatchMap]:
        result = await self.db.execute(
            select(BracketMatchMap).where(
                BracketMatchMap.match_id == match_id,
                BracketMatchMap.map_number == map_number,
            )
        )
        return result.scalar_one_or_none()

    async def update(self, map_id: str, data: dict) -> Optional[BracketMatchMap]:
        map_result = await self.get_by_match_and_number_by_id(map_id)
        if not map_result:
            return None
        for key, value in data.items():
            if hasattr(map_result, key):
                setattr(map_result, key, value)
        await self.db.flush()
        await self.db.refresh(map_result)
        return map_result

    async def get_by_match_and_number_by_id(self, map_id: str) -> Optional[BracketMatchMap]:
        result = await self.db.execute(select(BracketMatchMap).where(BracketMatchMap.id == map_id))
        return result.scalar_one_or_none()

    async def delete_by_match(self, match_id: str):
        await self.db.execute(delete(BracketMatchMap).where(BracketMatchMap.match_id == match_id))
