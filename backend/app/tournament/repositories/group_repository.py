from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List

from app.tournament.models.tournament_models import TournamentGroup

class TournamentGroupRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> TournamentGroup:
        group = TournamentGroup(**data)
        self.db.add(group)
        await self.db.flush()
        await self.db.refresh(group)
        return group

    async def get_by_tournament(self, tournament_id: str) -> List[TournamentGroup]:
        result = await self.db.execute(
            select(TournamentGroup)
            .where(TournamentGroup.tournament_id == tournament_id)
            .order_by(TournamentGroup.sort_order)
        )
        return list(result.scalars().all())

    async def get_by_id(self, group_id: str) -> Optional[TournamentGroup]:
        result = await self.db.execute(select(TournamentGroup).where(TournamentGroup.id == group_id))
        return result.scalar_one_or_none()

    async def delete_by_tournament(self, tournament_id: str):
        await self.db.execute(delete(TournamentGroup).where(TournamentGroup.tournament_id == tournament_id))
