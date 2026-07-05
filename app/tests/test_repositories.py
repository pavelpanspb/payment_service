import uuid
from unittest.mock import AsyncMock, MagicMock
from datetime import UTC, datetime

import pytest

from app.models import Outbox
from app.repositories.payment import PaymentRepository
from app.repositories.outbox import OutboxRepository


class TestPaymentRepository:
    async def test_try_create_with_idempotency(self, mock_session, sample_payment):
        repo = PaymentRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_payment
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.try_create_with_idempotency(sample_payment)

        mock_session.execute.assert_awaited_once()
        assert result is sample_payment

    async def test_try_create_with_idempotency_conflict(self, mock_session, sample_payment):
        repo = PaymentRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.try_create_with_idempotency(sample_payment)

        assert result is None

    async def test_get_by_idempotency_key(self, mock_session, sample_payment):
        repo = PaymentRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_payment
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_idempotency_key("test-key")

        assert result is sample_payment

    async def test_get_by_id_not_found(self, mock_session):
        repo = PaymentRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_id(uuid.uuid4())

        assert result is None

    async def test_update_webhook_retry(self, mock_session):
        repo = PaymentRepository(mock_session)
        mock_session.execute = AsyncMock()

        await repo.update_webhook_retry(uuid.uuid4(), 2, "timeout")

        mock_session.execute.assert_awaited_once()


class TestOutboxRepository:
    async def test_add(self, mock_session):
        repo = OutboxRepository(mock_session)
        outbox = Outbox(
            id=uuid.uuid4(),
            event_type="payment.created",
            aggregate_type="payment",
            aggregate_id=uuid.uuid4(),
            payload={"key": "value"},
            created_at=datetime.now(UTC),
        )

        await repo.add(outbox)

        mock_session.add.assert_called_once_with(outbox)

    async def test_get_unprocessed(self, mock_session):
        repo = OutboxRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_unprocessed(10)

        assert result == []

    async def test_mark_processed(self, mock_session):
        repo = OutboxRepository(mock_session)
        event_id = uuid.uuid4()
        mock_session.execute = AsyncMock()

        await repo.mark_processed(event_id)

        mock_session.execute.assert_awaited_once()

    async def test_mark_failed(self, mock_session):
        repo = OutboxRepository(mock_session)
        event_id = uuid.uuid4()
        mock_session.execute = AsyncMock()

        await repo.mark_failed(event_id, "connection error")

        mock_session.execute.assert_awaited_once()
