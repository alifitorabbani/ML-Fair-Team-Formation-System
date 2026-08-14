from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.models import AuditLog
from datetime import datetime
import json


class AuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, action: str, actor: Optional[str] = None,
                     metadata: Optional[dict] = None) -> AuditLog:
        log = AuditLog(
            action=action,
            actor=actor,
            log_metadata=json.dumps(metadata) if metadata else None,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def get_all(self, limit: int = 100) -> List[AuditLog]:
        result = await self.db.execute(
            select(AuditLog).order_by(desc(AuditLog.timestamp)).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_action(self, action: str, limit: int = 100) -> List[AuditLog]:
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(desc(AuditLog.timestamp))
            .limit(limit)
        )
        return list(result.scalars().all())
