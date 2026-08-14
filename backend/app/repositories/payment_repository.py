from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.models import Payment
from app.schemas.schemas import PaymentStatus
from datetime import datetime


class PaymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_player_id(self, player_id: str) -> Optional[Payment]:
        result = await self.db.execute(
            select(Payment).where(Payment.player_id == player_id).order_by(desc(Payment.created_at))
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> List[Payment]:
        result = await self.db.execute(select(Payment).order_by(desc(Payment.created_at)))
        return list(result.scalars().all())

    async def create_or_update(self, player_id: str, status: str = PaymentStatus.pending.value,
                               amount: Optional[float] = None, method: Optional[str] = None,
                               transaction_id: Optional[str] = None, notes: Optional[str] = None) -> Payment:
        payment = await self.get_by_player_id(player_id)
        if payment:
            payment.status = status
            if amount is not None:
                payment.amount = amount
            if method is not None:
                payment.method = method
            if transaction_id is not None:
                payment.transaction_id = transaction_id
            if notes is not None:
                payment.notes = notes
            if status == PaymentStatus.paid.value:
                payment.paid_at = datetime.utcnow()
        else:
            payment = Payment(
                player_id=player_id,
                status=status,
                amount=amount,
                method=method,
                transaction_id=transaction_id,
                notes=notes,
            )
            self.db.add(payment)
        await self.db.flush()
        return payment

    async def verify(self, player_id: str, status: str, verified_by: Optional[str] = None,
                     transaction_id: Optional[str] = None, notes: Optional[str] = None) -> Optional[Payment]:
        payment = await self.get_by_player_id(player_id)
        if payment:
            payment.status = status
            payment.verified_by = verified_by
            payment.verified_at = datetime.utcnow()
            if transaction_id:
                payment.transaction_id = transaction_id
            if notes:
                payment.notes = notes
            if status == PaymentStatus.paid.value:
                payment.paid_at = datetime.utcnow()
            await self.db.flush()
        return payment

    async def delete(self, payment_id: str) -> bool:
        payment = await self.db.get(Payment, payment_id)
        if not payment:
            return False
        await self.db.delete(payment)
        await self.db.flush()
        return True
