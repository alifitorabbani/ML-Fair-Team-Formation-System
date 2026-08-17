from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List

from app.tournament.models.tournament_models import TournamentDate

class TournamentDateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> TournamentDate:
        date_obj = TournamentDate(**data)
        self.db.add(date_obj)
        await self.db.flush()
        await self.db.refresh(date_obj)
        return date_obj

    async def get_by_tournament(self, tournament_id: str) -> List[TournamentDate]:
        result = await self.db.execute(
            select(TournamentDate).where(TournamentDate.tournament_id == tournament_id).order_by(TournamentDate.date)
        )
        return list(result.scalars().all())

    async def get_by_tournament_and_date(self, tournament_id: str, date_val) -> Optional[TournamentDate]:
        result = await self.db.execute(
            select(TournamentDate).where(
                TournamentDate.tournament_id == tournament_id,
                TournamentDate.date == date_val,
            )
        )
        return result.scalar_one_or_none()

    async def delete_by_tournament(self, tournament_id: str):
        await self.db.execute(delete(TournamentDate).where(TournamentDate.tournament_id == tournament_id))
