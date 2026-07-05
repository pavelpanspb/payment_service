import uuid
from datetime import UTC, datetime

from app.models import Outbox, Payment, PaymentStatus
from app.schemas import CreatePaymentRequest
from app.unit_of_work import UnitOfWork


class PaymentService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_payment(
        self, body: CreatePaymentRequest, idempotency_key: str
    ) -> Payment:
        payment = Payment(
            id=uuid.uuid4(),
            amount=body.amount,
            currency=body.currency,
            description=body.description,
            metadata_=body.metadata,
            status=PaymentStatus.pending,
            idempotency_key=idempotency_key,
            webhook_url=str(body.webhook_url),
            created_at=datetime.now(UTC),
        )

        created = await self.uow.payments.try_create_with_idempotency(payment)
        if created is not None:
            outbox = Outbox(
                id=uuid.uuid4(),
                event_type="payment.created",
                aggregate_type="payment",
                aggregate_id=payment.id,
                payload={
                    "payment_id": str(payment.id),
                    "amount": str(body.amount),
                    "currency": body.currency,
                    "description": body.description,
                    "metadata": body.metadata,
                    "webhook_url": str(body.webhook_url),
                    "idempotency_key": idempotency_key,
                },
                created_at=datetime.now(UTC),
            )
            await self.uow.outbox.add(outbox)
            return created

        return await self.uow.payments.get_by_idempotency_key(idempotency_key)

    async def get_payment(self, payment_id: uuid.UUID) -> Payment | None:
        return await self.uow.payments.get_by_id(payment_id)
