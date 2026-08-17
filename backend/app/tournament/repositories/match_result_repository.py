from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List

from app.tournament.models.tournament_models import MatchResultVersion

class MatchResultVersionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> MatchResultVersion:
        version = MatchResultVersion(**data)
        self.db.add(version)
        await self.db.flush()
        await self.db.refresh(version)
        return version

    async def get_by_match(self, match_id: str) -> List[MatchResultVersion]:
        result = await self.db.execute(
            select(MatchResultVersion).where(MatchResultVersion.match_id == match_id).order_by(MatchResultVersion.version)
        )
        return list(result.scalars().all())

    async def get_latest_by_match(self, match_id: str) -> Optional[MatchResultVersion]:
        result = await self.db.execute(
            select(MatchResultVersion)
            .where(MatchResultVersion.match_id == match_id)
            .order_by(MatchResultVersion.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_next_version(self, match_id: str) -> int:
        versions = await self.get_by_match(match_id)
        if not versions:
            return 1
        return max(v.version for v in versions) + 1
