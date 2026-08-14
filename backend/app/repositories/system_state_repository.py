from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import SystemState
from app.schemas.schemas import SystemState as SystemStateEnum


class SystemStateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self) -> Optional[SystemState]:
        result = await self.db.execute(select(SystemState).where(SystemState.id == "global"))
        return result.scalar_one_or_none()

    async def get_or_create(self) -> SystemState:
        state = await self.get()
        if not state:
            state = SystemState(id="global", state=SystemStateEnum.draft.value)
            self.db.add(state)
            await self.db.flush()
        return state

    async def update_state(self, state: str, ranking_version_id: Optional[str] = None,
                           team_version_id: Optional[str] = None) -> SystemState:
        s = await self.get_or_create()
        s.state = state
        if ranking_version_id is not None:
            s.current_ranking_version_id = ranking_version_id
        if team_version_id is not None:
            s.current_team_version_id = team_version_id
        await self.db.flush()
        return s
