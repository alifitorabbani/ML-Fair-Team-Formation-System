from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List

from app.tournament.models.tournament_models import TournamentPlacement

class TournamentPlacementRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> TournamentPlacement:
        placement = TournamentPlacement(**data)
        self.db.add(placement)
        await self.db.flush()
        await self.db.refresh(placement)
        return placement

    async def get_by_tournament(self, tournament_id: str) -> List[TournamentPlacement]:
        result = await self.db.execute(
            select(TournamentPlacement)
            .where(TournamentPlacement.tournament_id == tournament_id)
            .order_by(TournamentPlacement.placement)
        )
        return list(result.scalars().all())

    async def get_by_tournament_and_team(self, tournament_id: str, team_id: str) -> Optional[TournamentPlacement]:
        result = await self.db.execute(
            select(TournamentPlacement).where(
                TournamentPlacement.tournament_id == tournament_id,
                TournamentPlacement.team_id == team_id,
            )
        )
        return result.scalar_one_or_none()
