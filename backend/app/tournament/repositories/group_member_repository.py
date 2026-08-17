from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List

from app.tournament.models.tournament_models import TournamentGroupMember

class TournamentGroupMemberRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> TournamentGroupMember:
        member = TournamentGroupMember(**data)
        self.db.add(member)
        await self.db.flush()
        await self.db.refresh(member)
        return member

    async def get_by_group(self, group_id: str) -> List[TournamentGroupMember]:
        result = await self.db.execute(
            select(TournamentGroupMember)
            .where(TournamentGroupMember.group_id == group_id)
            .order_by(TournamentGroupMember.seed)
        )
        return list(result.scalars().all())

    async def get_by_tournament_team(self, tournament_team_id: str) -> List[TournamentGroupMember]:
        result = await self.db.execute(
            select(TournamentGroupMember).where(TournamentGroupMember.tournament_team_id == tournament_team_id)
        )
        return list(result.scalars().all())

    async def delete_by_group(self, group_id: str):
        await self.db.execute(delete(TournamentGroupMember).where(TournamentGroupMember.group_id == group_id))

    async def delete_by_tournament(self, tournament_id: str):
        await self.db.execute(
            delete(TournamentGroupMember).where(
                TournamentGroupMember.group_id.in_(
                    select(TournamentGroup.id).where(TournamentGroup.tournament_id == tournament_id)
                )
            )
        )
