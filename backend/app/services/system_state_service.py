from typing import Optional
from app.repositories.system_state_repository import SystemStateRepository
from app.repositories.audit_repository import AuditRepository
from app.schemas.schemas import SystemState as SystemStateEnum
from uuid import uuid4


class SystemStateService:
    def __init__(self, state_repo: SystemStateRepository, audit_repo: AuditRepository):
        self.state_repo = state_repo
        self.audit_repo = audit_repo

    async def get_current_state(self) -> dict:
        state = await self.state_repo.get_or_create()
        return {
            "state": state.state,
            "current_ranking_version_id": state.current_ranking_version_id,
            "current_team_version_id": state.current_team_version_id,
            "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        }

    async def set_ranking_generated(self, ranking_version_id: str, actor: Optional[str] = None) -> dict:
        state = await self.state_repo.update_state(
            SystemStateEnum.ranking_generated.value,
            ranking_version_id=ranking_version_id,
        )
        await self.audit_repo.create(
            action="RANKING_GENERATED",
            actor=actor,
            metadata={"ranking_version_id": ranking_version_id},
        )
        return {
            "state": state.state,
            "current_ranking_version_id": state.current_ranking_version_id,
            "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        }

    async def set_team_generated(self, team_version_id: str, actor: Optional[str] = None) -> dict:
        state = await self.state_repo.update_state(
            SystemStateEnum.team_generated.value,
            team_version_id=team_version_id,
        )
        await self.audit_repo.create(
            action="TEAM_GENERATED",
            actor=actor,
            metadata={"team_version_id": team_version_id},
        )
        return {
            "state": state.state,
            "current_team_version_id": state.current_team_version_id,
            "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        }

    async def set_payment_open(self, actor: Optional[str] = None) -> dict:
        state = await self.state_repo.update_state(SystemStateEnum.payment_open.value)
        await self.audit_repo.create(
            action="PAYMENT_OPENED",
            actor=actor,
            metadata={},
        )
        return {
            "state": state.state,
            "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        }

    async def set_competition_ready(self, actor: Optional[str] = None) -> dict:
        state = await self.state_repo.update_state(SystemStateEnum.competition_ready.value)
        await self.audit_repo.create(
            action="COMPETITION_READY",
            actor=actor,
            metadata={},
        )
        return {
            "state": state.state,
            "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        }

    async def can_view_ranking(self) -> bool:
        state = await self.get_current_state()
        return state["state"] in [
            SystemStateEnum.ranking_generated.value,
            SystemStateEnum.team_generated.value,
            SystemStateEnum.payment_open.value,
            SystemStateEnum.competition_ready.value,
        ]

    async def can_view_team(self) -> bool:
        state = await self.get_current_state()
        return state["state"] in [
            SystemStateEnum.team_generated.value,
            SystemStateEnum.payment_open.value,
            SystemStateEnum.competition_ready.value,
        ]
