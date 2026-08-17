from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List

from app.tournament.models.tournament_models import BracketQualification


class BracketQualificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> BracketQualification:
        qualification = BracketQualification(**data)
        self.db.add(qualification)
        await self.db.flush()
        await self.db.refresh(qualification)
        return qualification

    async def get_by_tournament(self, tournament_id: str) -> List[BracketQualification]:
        result = await self.db.execute(
            select(BracketQualification).where(BracketQualification.tournament_id == tournament_id)
        )
        return list(result.scalars().all())

    async def get_by_tournament_and_bracket(self, tournament_id: str, bracket_type: str) -> List[BracketQualification]:
        result = await self.db.execute(
            select(BracketQualification)
            .where(BracketQualification.tournament_id == tournament_id)
            .where(BracketQualification.bracket_type == bracket_type)
        )
        return list(result.scalars().all())

    async def get_by_group(self, group_id: str) -> List[BracketQualification]:
        result = await self.db.execute(
            select(BracketQualification).where(BracketQualification.group_id == group_id)
        )
        return list(result.scalars().all())

    async def get_by_team(self, tournament_id: str, team_id: str) -> Optional[BracketQualification]:
        result = await self.db.execute(
            select(BracketQualification)
            .where(BracketQualification.tournament_id == tournament_id)
            .where(BracketQualification.team_id == team_id)
        )
        return result.scalar_one_or_none()

    async def delete_by_tournament(self, tournament_id: str):
        await self.db.execute(delete(BracketQualification).where(BracketQualification.tournament_id == tournament_id))

    async def delete_by_group(self, group_id: str):
        await self.db.execute(delete(BracketQualification).where(BracketQualification.group_id == group_id))
