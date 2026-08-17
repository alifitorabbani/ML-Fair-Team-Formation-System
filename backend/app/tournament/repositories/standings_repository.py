from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List

from app.tournament.models.tournament_models import GroupStanding

class GroupStandingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_or_update(self, data: dict) -> GroupStanding:
        group_id = data["group_id"]
        team_id = data["team_id"]
        existing = await self.get_by_group_and_team(group_id, team_id)
        if existing:
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.computed_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        standing = GroupStanding(**data)
        self.db.add(standing)
        await self.db.flush()
        await self.db.refresh(standing)
        return standing

    async def get_by_group_and_team(self, group_id: str, team_id: str) -> Optional[GroupStanding]:
        result = await self.db.execute(
            select(GroupStanding).where(GroupStanding.group_id == group_id, GroupStanding.team_id == team_id)
        )
        return result.scalar_one_or_none()

    async def get_by_group(self, group_id: str) -> List[GroupStanding]:
        result = await self.db.execute(
            select(GroupStanding)
            .where(GroupStanding.group_id == group_id)
            .order_by(GroupStanding.points.desc(), GroupStanding.kill_difference.desc())
        )
        return list(result.scalars().all())

    async def delete_by_group(self, group_id: str):
        await self.db.execute(delete(GroupStanding).where(GroupStanding.group_id == group_id))
