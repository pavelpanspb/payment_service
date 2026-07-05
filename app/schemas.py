from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class CreatePaymentRequest(BaseModel):
    amount: Decimal = Field(..., decimal_places=2, gt=0)
    currency: str = Field(..., pattern=r"^(RUB|USD|EUR)$")
    description: str | None = None
    metadata: dict[str, Any] | None = None
    webhook_url: HttpUrl


class PaymentResponse(BaseModel):
    id: str
    status: str
    amount: float
    currency: str
    description: str | None
    metadata: dict[str, Any] | None
    webhook_url: str
    webhook_retry_count: int
    webhook_last_error: str | None
    created_at: datetime
    processed_at: datetime | None

    model_config = {"from_attributes": True}


class PaymentCreatedResponse(BaseModel):
    payment_id: str
    status: str
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str
