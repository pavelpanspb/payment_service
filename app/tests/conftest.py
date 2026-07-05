import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models import Payment, PaymentStatus
from app.schemas import CreatePaymentRequest
from app.unit_of_work import UnitOfWork

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_uow(mock_session):
    uow = UnitOfWork(mock_session)
    uow.payments = AsyncMock()
    uow.outbox = AsyncMock()
    return uow


@pytest.fixture
def create_payment_request():
    return CreatePaymentRequest(
        amount="100.50",
        currency="USD",
        description="Test payment",
        metadata={"order_id": "123"},
        webhook_url="https://example.com/webhook",
    )


@pytest.fixture
def sample_payment():
    return Payment(
        id=uuid.uuid4(),
        amount=100.50,
        currency="USD",
        description="Test payment",
        metadata_={"order_id": "123"},
        status=PaymentStatus.pending,
        idempotency_key="test-key-123",
        webhook_url="https://example.com/webhook",
        created_at=datetime.now(UTC),
    )
