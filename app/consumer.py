import asyncio
import logging
import random
from datetime import datetime

from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue

from app.config import settings
from app.db import async_session_factory
from app.models import Payment, PaymentStatus
from app.repositories.payment import PaymentRepository
from app.services.webhook import WebhookSender

logger = logging.getLogger("payment_consumer")

broker = RabbitBroker(settings.rabbitmq_url)
app = FastStream(broker)

webhook_sender = WebhookSender()


@broker.subscriber(
    RabbitQueue(
        "payments.new",
        durable=True,
        arguments={"x-dead-letter-exchange": "payments.dlx"},
    ),
    RabbitExchange("payments", "topic", durable=True),
    retry=3,
)
async def handle_payment(message: dict) -> None:
    payment_id = message.get("payment_id")
    webhook_url = message.get("webhook_url")

    if not payment_id:
        logger.error("Missing payment_id in message")
        return

    async with async_session_factory() as session:
        repo = PaymentRepository(session)
        payment = await repo.get_by_id(payment_id)

        if payment is None:
            logger.error("Payment %s not found in DB", payment_id)
            return

        if payment.status == PaymentStatus.pending:
            delay = random.uniform(2, 5)
            await asyncio.sleep(delay)

            is_success = random.random() < 0.9
            payment.status = PaymentStatus.succeeded if is_success else PaymentStatus.failed
            payment.processed_at = datetime.utcnow()

            logger.info("Payment %s processed → %s", payment_id, payment.status.value)

        success = await webhook_sender.send(
            webhook_url,
            {
                "payment_id": str(payment.id),
                "status": payment.status.value,
                "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
            },
        )

        if success:
            payment.webhook_retry_count = 0
            payment.webhook_last_error = None
            logger.info("Webhook OK for payment %s", payment_id)
        else:
            payment.webhook_retry_count = (payment.webhook_retry_count or 0) + 1
            payment.webhook_last_error = "Webhook failed after 3 attempts"
            logger.error(
                "Webhook permanently failed for payment %s (retry=%d)",
                payment_id,
                payment.webhook_retry_count,
            )

        await session.commit()


@broker.subscriber(
    RabbitQueue("payments.dead", durable=True),
    RabbitExchange("payments.dlx", "fanout", durable=True),
)
async def handle_dead_letter(message: dict) -> None:
    logger.warning("Dead letter: payment_id=%s", message.get("payment_id"))
