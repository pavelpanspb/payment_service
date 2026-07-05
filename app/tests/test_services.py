import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.payment import PaymentService
from app.services.webhook import WebhookSender


class TestPaymentService:
    async def test_create_new_payment(self, mock_uow, create_payment_request):
        created = MagicMock()
        created.id = uuid.uuid4()
        created.status = MagicMock(value="pending")
        created.created_at = MagicMock()
        mock_uow.payments.try_create_with_idempotency = AsyncMock(return_value=created)

        service = PaymentService(mock_uow)
        result = await service.create_payment(create_payment_request, "key-1")

        assert result is created
        mock_uow.payments.try_create_with_idempotency.assert_awaited_once()
        mock_uow.outbox.add.assert_awaited_once()

    async def test_duplicate_idempotency_key(self, mock_uow, create_payment_request, sample_payment):
        mock_uow.payments.try_create_with_idempotency = AsyncMock(return_value=None)
        mock_uow.payments.get_by_idempotency_key = AsyncMock(return_value=sample_payment)

        service = PaymentService(mock_uow)
        result = await service.create_payment(create_payment_request, "dup-key")

        assert result is sample_payment
        mock_uow.outbox.add.assert_not_awaited()

    async def test_get_payment_found(self, mock_uow, sample_payment):
        payment_id = sample_payment.id
        mock_uow.payments.get_by_id = AsyncMock(return_value=sample_payment)

        service = PaymentService(mock_uow)
        result = await service.get_payment(payment_id)

        assert result is sample_payment
        mock_uow.payments.get_by_id.assert_awaited_once_with(payment_id)

    async def test_get_payment_not_found(self, mock_uow):
        payment_id = uuid.uuid4()
        mock_uow.payments.get_by_id = AsyncMock(return_value=None)

        service = PaymentService(mock_uow)
        result = await service.get_payment(payment_id)

        assert result is None


class TestWebhookSender:
    async def test_send_success_first_attempt(self):
        sender = WebhookSender()
        payload = {"status": "succeeded"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await sender.send("https://example.com/hook", payload)

        assert result is True
        mock_client.post.assert_awaited_once()

    async def test_send_retry_on_failure(self):
        sender = WebhookSender()
        payload = {"status": "failed"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.is_success = False
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await sender.send("https://example.com/hook", payload)

        assert result is False
        assert mock_client.post.await_count == 3

    async def test_send_success_on_second_attempt(self):
        sender = WebhookSender()
        payload = {"status": "succeeded"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_responses = [MagicMock(), MagicMock()]
            mock_responses[0].is_success = False
            mock_responses[1].is_success = True
            mock_client.post = AsyncMock(side_effect=mock_responses)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await sender.send("https://example.com/hook", payload)

        assert result is True
        assert mock_client.post.await_count == 2
