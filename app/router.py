import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import verify_api_key
from app.models import Outbox, Payment, PaymentStatus
from app.schemas import CreatePaymentRequest, PaymentCreatedResponse, PaymentResponse

router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_api_key)])


@router.post("/payments", status_code=202, response_model=PaymentCreatedResponse)
async def create_payment(
    body: CreatePaymentRequest,
    idempotency_key: str = Header(...),
    session: AsyncSession = Depends(get_session),
):
    existing = await session.execute(
        select(Payment).where(Payment.idempotency_key == idempotency_key)
    )
    existing_payment = existing.scalar_one_or_none()
    if existing_payment:
        return PaymentCreatedResponse(
            payment_id=str(existing_payment.id),
            status=existing_payment.status.value,
            created_at=existing_payment.created_at,
        )

    payment = Payment(
        id=uuid.uuid4(),
        amount=body.amount,
        currency=body.currency,
        description=body.description,
        metadata=body.metadata,
        status=PaymentStatus.pending,
        idempotency_key=idempotency_key,
        webhook_url=str(body.webhook_url),
        created_at=datetime.utcnow(),
    )
    session.add(payment)

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
        created_at=datetime.utcnow(),
    )
    session.add(outbox)

    await session.commit()

    return PaymentCreatedResponse(
        payment_id=str(payment.id),
        status=payment.status.value,
        created_at=payment.created_at,
    )


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    session: AsyncSession = Depends(get_session),
):
    try:
        uid = uuid.UUID(payment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payment ID")

    result = await session.execute(select(Payment).where(Payment.id == uid))
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    return PaymentResponse(
        id=str(payment.id),
        status=payment.status.value,
        amount=float(payment.amount),
        currency=payment.currency,
        description=payment.description,
        metadata=payment.metadata,
        webhook_url=payment.webhook_url,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
    )
