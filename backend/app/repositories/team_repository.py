from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.models import TeamVersion, TeamMember
from app.schemas.schemas import TeamStatus
from datetime import datetime


class TeamRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active(self) -> Optional[TeamVersion]:
        result = await self.db.execute(
            select(TeamVersion)
            .where(TeamVersion.is_active == True)
            .order_by(desc(TeamVersion.generated_at))
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, version_id: str) -> Optional[TeamVersion]:
        result = await self.db.execute(select(TeamVersion).where(TeamVersion.id == version_id))
        return result.scalar_one_or_none()

    async def get_all(self) -> List[TeamVersion]:
        result = await self.db.execute(select(TeamVersion).order_by(desc(TeamVersion.generated_at)))
        return list(result.scalars().all())

    async def create(self, version_id: str, ranking_version_id: str, total_teams: int,
                     total_participants: int, selected_count: int, not_selected_count: int,
                     generated_by: Optional[str] = None, random_seed: Optional[int] = None,
                     overall_fairness: Optional[float] = None,
                     optimization_iterations: Optional[int] = None,
                     processing_time_ms: Optional[float] = None) -> TeamVersion:
        version = TeamVersion(
            id=version_id,
            ranking_version_id=ranking_version_id,
            total_teams=total_teams,
            total_participants=total_participants,
            selected_count=selected_count,
            not_selected_count=not_selected_count,
            generated_by=generated_by,
            random_seed=random_seed,
            overall_fairness=overall_fairness,
            optimization_iterations=optimization_iterations,
            processing_time_ms=processing_time_ms,
            status=TeamStatus.draft.value,
            is_active=True,
        )
        self.db.add(version)
        await self.db.flush()
        return version

    async def confirm(self, version_id: str) -> Optional[TeamVersion]:
        version = await self.get_by_id(version_id)
        if version:
            version.status = TeamStatus.confirmed.value
            version.confirmed_at = datetime.utcnow()
            await self.db.flush()
        return version

    async def deactivate_all(self) -> None:
        result = await self.db.execute(select(TeamVersion).where(TeamVersion.is_active == True))
        versions = result.scalars().all()
        for v in versions:
            v.is_active = False
        await self.db.flush()

    async def add_member(self, member: TeamMember) -> TeamMember:
        self.db.add(member)
        await self.db.flush()
        return member

    async def get_members_by_version(self, version_id: str) -> List[TeamMember]:
        result = await self.db.execute(
            select(TeamMember).where(TeamMember.team_version_id == version_id)
        )
        return list(result.scalars().all())

    async def get_members_by_player(self, player_id: str) -> List[TeamMember]:
        result = await self.db.execute(
            select(TeamMember).where(TeamMember.player_id == player_id)
        )
        return list(result.scalars().all())
