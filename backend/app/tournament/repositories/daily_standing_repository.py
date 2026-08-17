from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List

from app.tournament.models.tournament_models import DailyStanding


class DailyStandingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_or_update(self, data: dict) -> DailyStanding:
        tournament_id = data["tournament_id"]
        group_id = data.get("group_id")
        team_id = data["team_id"]
        match_date = data["match_date"]
        existing = await self.get_by_tournament_group_team_date(tournament_id, group_id, team_id, match_date)
        if existing:
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.computed_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        standing = DailyStanding(**data)
        self.db.add(standing)
        await self.db.flush()
        await self.db.refresh(standing)
        return standing

    async def get_by_tournament_group_team_date(self, tournament_id: str, group_id: Optional[str], team_id: str, match_date: str) -> Optional[DailyStanding]:
        result = await self.db.execute(
            select(DailyStanding).where(
                DailyStanding.tournament_id == tournament_id,
                DailyStanding.group_id == group_id,
                DailyStanding.team_id == team_id,
                DailyStanding.match_date == match_date,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_tournament_and_date(self, tournament_id: str, match_date: str) -> List[DailyStanding]:
        result = await self.db.execute(
            select(DailyStanding)
            .where(DailyStanding.tournament_id == tournament_id, DailyStanding.match_date == match_date)
            .order_by(DailyStanding.points.desc(), DailyStanding.kill_difference.desc())
        )
        return list(result.scalars().all())

    async def get_by_tournament(self, tournament_id: str) -> List[DailyStanding]:
        result = await self.db.execute(
            select(DailyStanding)
            .where(DailyStanding.tournament_id == tournament_id)
            .order_by(DailyStanding.match_date.asc(), DailyStanding.points.desc(), DailyStanding.kill_difference.desc())
        )
        return list(result.scalars().all())

    async def delete_by_tournament(self, tournament_id: str):
        await self.db.execute(delete(DailyStanding).where(DailyStanding.tournament_id == tournament_id))
