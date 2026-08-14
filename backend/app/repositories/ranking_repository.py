from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.models import RankingVersion
from app.schemas.schemas import RankingStatus
from datetime import datetime


class RankingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active(self) -> Optional[RankingVersion]:
        result = await self.db.execute(
            select(RankingVersion)
            .where(RankingVersion.is_active == True)
            .order_by(desc(RankingVersion.generated_at))
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, version_id: str) -> Optional[RankingVersion]:
        result = await self.db.execute(select(RankingVersion).where(RankingVersion.id == version_id))
        return result.scalar_one_or_none()

    async def get_all(self) -> List[RankingVersion]:
        result = await self.db.execute(select(RankingVersion).order_by(desc(RankingVersion.generated_at)))
        return list(result.scalars().all())

    async def create(self, version_id: str, total_participants: int, qualified_count: int,
                     eliminated_count: int, generated_by: Optional[str] = None,
                     seed: Optional[int] = None, score_components: Optional[str] = None) -> RankingVersion:
        version = RankingVersion(
            id=version_id,
            total_participants=total_participants,
            qualified_count=qualified_count,
            eliminated_count=eliminated_count,
            generated_by=generated_by,
            seed=seed,
            score_components=score_components,
            status=RankingStatus.draft.value,
            is_active=True,
        )
        self.db.add(version)
        await self.db.flush()
        return version

    async def confirm(self, version_id: str) -> Optional[RankingVersion]:
        version = await self.get_by_id(version_id)
        if version:
            version.status = RankingStatus.confirmed.value
            version.confirmed_at = datetime.utcnow()
            await self.db.flush()
        return version

    async def deactivate_all(self) -> None:
        result = await self.db.execute(select(RankingVersion).where(RankingVersion.is_active == True))
        versions = result.scalars().all()
        for v in versions:
            v.is_active = False
        await self.db.flush()
