from typing import List, Optional
from app.repositories.payment_repository import PaymentRepository
from app.repositories.audit_repository import AuditRepository
from app.schemas.schemas import PaymentStatus
from uuid import uuid4


class PaymentService:
    def __init__(self, payment_repo: PaymentRepository, audit_repo: AuditRepository):
        self.payment_repo = payment_repo
        self.audit_repo = audit_repo

    async def get_payment(self, player_id: str) -> Optional[dict]:
        payment = await self.payment_repo.get_by_player_id(player_id)
        if not payment:
            return None
        return {
            "id": payment.id,
            "player_id": payment.player_id,
            "status": payment.status,
            "amount": payment.amount,
            "method": payment.method,
            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
            "verified_by": payment.verified_by,
            "verified_at": payment.verified_at.isoformat() if payment.verified_at else None,
            "transaction_id": payment.transaction_id,
            "notes": payment.notes,
            "created_at": payment.created_at.isoformat(),
        }

    async def verify_payment(self, player_id: str, status: str, verified_by: Optional[str] = None,
                             transaction_id: Optional[str] = None,
                             notes: Optional[str] = None) -> dict:
        payment = await self.payment_repo.verify(
            player_id, status, verified_by=verified_by,
            transaction_id=transaction_id, notes=notes,
        )
        if not payment:
            return {"success": False, "message": "Payment not found"}

        await self.audit_repo.create(
            action="PAYMENT_VERIFIED",
            actor=verified_by,
            metadata={
                "player_id": player_id,
                "status": status,
                "payment_id": payment.id,
            },
        )
        return {
            "success": True,
            "id": payment.id,
            "player_id": payment.player_id,
            "status": payment.status,
            "amount": payment.amount,
            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
            "verified_at": payment.verified_at.isoformat() if payment.verified_at else None,
            "verified_by": payment.verified_by,
            "transaction_id": payment.transaction_id,
            "notes": payment.notes,
        }

    async def get_all_payments(self) -> List[dict]:
        payments = await self.payment_repo.get_all()
        return [
            {
                "id": p.id,
                "player_id": p.player_id,
                "status": p.status,
                "amount": p.amount,
                "method": p.method,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "verified_by": p.verified_by,
                "verified_at": p.verified_at.isoformat() if p.verified_at else None,
                "transaction_id": p.transaction_id,
                "notes": p.notes,
                "created_at": p.created_at.isoformat(),
            }
            for p in payments
        ]

    async def get_payment_stats(self) -> dict:
        payments = await self.payment_repo.get_all()
        total = len(payments)
        pending = sum(1 for p in payments if p.status == PaymentStatus.pending.value)
        paid = sum(1 for p in payments if p.status == PaymentStatus.paid.value)
        failed = sum(1 for p in payments if p.status == PaymentStatus.failed.value)
        return {
            "total": total,
            "pending": pending,
            "paid": paid,
            "failed": failed,
        }
