from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List

from app.tournament.models.tournament_models import ScheduleVersion

class ScheduleVersionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> ScheduleVersion:
        version = ScheduleVersion(**data)
        self.db.add(version)
        await self.db.flush()
        await self.db.refresh(version)
        return version

    async def get_by_tournament(self, tournament_id: str) -> List[ScheduleVersion]:
        result = await self.db.execute(
            select(ScheduleVersion).where(ScheduleVersion.tournament_id == tournament_id).order_by(ScheduleVersion.version)
        )
        return list(result.scalars().all())

    async def get_latest_by_tournament(self, tournament_id: str) -> Optional[ScheduleVersion]:
        result = await self.db.execute(
            select(ScheduleVersion)
            .where(ScheduleVersion.tournament_id == tournament_id)
            .order_by(ScheduleVersion.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
