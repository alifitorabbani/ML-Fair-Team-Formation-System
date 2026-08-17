from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List

from app.tournament.models.tournament_models import TournamentTeam

class TournamentTeamRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> TournamentTeam:
        team = TournamentTeam(**data)
        self.db.add(team)
        await self.db.flush()
        await self.db.refresh(team)
        return team

    async def get_by_tournament(self, tournament_id: str) -> List[TournamentTeam]:
        result = await self.db.execute(
            select(TournamentTeam).where(TournamentTeam.tournament_id == tournament_id).order_by(TournamentTeam.seed)
        )
        return list(result.scalars().all())

    async def get_by_tournament_and_team(self, tournament_id: str, team_id: str) -> Optional[TournamentTeam]:
        result = await self.db.execute(
            select(TournamentTeam).where(
                TournamentTeam.tournament_id == tournament_id,
                TournamentTeam.team_id == team_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_by_tournament(self, tournament_id: str):
        await self.db.execute(delete(TournamentTeam).where(TournamentTeam.tournament_id == tournament_id))
