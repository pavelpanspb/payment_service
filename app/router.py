import uuid

from fastapi import APIRouter, Depends, Header, HTTPException

from app.db import get_session
from app.dependencies import verify_api_key
from app.schemas import (
    CreatePaymentRequest,
    PaymentCreatedResponse,
    PaymentResponse,
)
from app.services.payment import PaymentService
from app.unit_of_work import UnitOfWork

router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_api_key)])


def get_uow(session=Depends(get_session)) -> UnitOfWork:
    return UnitOfWork(session)


@router.post("/payments", status_code=202, response_model=PaymentCreatedResponse)
async def create_payment(
    body: CreatePaymentRequest,
    idempotency_key: str = Header(...),
    uow: UnitOfWork = Depends(get_uow),
):
    service = PaymentService(uow)
    payment = await service.create_payment(body, idempotency_key)
    await uow.commit()

    return PaymentCreatedResponse(
        payment_id=str(payment.id),
        status=payment.status.value,
        created_at=payment.created_at,
    )


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    uow: UnitOfWork = Depends(get_uow),
):
    try:
        uid = uuid.UUID(payment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payment ID")

    service = PaymentService(uow)
    payment = await service.get_payment(uid)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    return PaymentResponse(
        id=str(payment.id),
        status=payment.status.value,
        amount=float(payment.amount),
        currency=payment.currency,
        description=payment.description,
        metadata=payment.metadata_,
        webhook_url=payment.webhook_url,
        webhook_retry_count=payment.webhook_retry_count,
        webhook_last_error=payment.webhook_last_error,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
    )
