import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum as SAEnum, Integer, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db import Base


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    description = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    status = Column(SAEnum(PaymentStatus), default=PaymentStatus.pending, nullable=False)
    idempotency_key = Column(String(255), unique=True, nullable=False, index=True)
    webhook_url = Column(String(1024), nullable=False)
    webhook_retry_count = Column(Integer, default=0, nullable=False)
    webhook_last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    processed_at = Column(DateTime, nullable=True)


class Outbox(Base):
    __tablename__ = "outbox"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(255), nullable=False)
    aggregate_type = Column(String(255), nullable=False)
    aggregate_id = Column(UUID(as_uuid=True), nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    processed_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
