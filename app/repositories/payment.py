import uuid

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Payment, PaymentStatus


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def try_create_with_idempotency(self, payment: Payment) -> Payment | None:
        stmt = (
            pg_insert(Payment)
            .values(
                id=payment.id,
                amount=payment.amount,
                currency=payment.currency,
                description=payment.description,
                metadata=payment.metadata_,
                status=payment.status.value,
                idempotency_key=payment.idempotency_key,
                webhook_url=payment.webhook_url,
                created_at=payment.created_at,
            )
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
            .returning(Payment)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        result = await self.session.execute(
            select(Payment).where(Payment.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        result = await self.session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def update_webhook_retry(
        self, payment_id: uuid.UUID, retry_count: int, last_error: str | None
    ) -> None:
        await self.session.execute(
            update(Payment)
            .where(Payment.id == payment_id)
            .values(webhook_retry_count=retry_count, webhook_last_error=last_error)
        )
