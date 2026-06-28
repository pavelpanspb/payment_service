import asyncio
import logging
import random
from datetime import datetime

import httpx
from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitQueue
from sqlalchemy import select

from app.config import settings
from app.db import async_session_factory
from app.models import Payment, PaymentStatus

logger = logging.getLogger("payment_consumer")

broker = RabbitBroker(settings.rabbitmq_url)

app = FastStream(broker)

MAX_WEBHOOK_RETRIES = 3


async def send_webhook(url: str, payload: dict) -> bool:
    for attempt in range(1, MAX_WEBHOOK_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                logger.info("Webhook sent to %s, status=%d (attempt %d)", url, resp.status_code, attempt)
                if resp.is_success:
                    return True
        except Exception as e:
            logger.warning("Webhook attempt %d failed: %s", attempt, e)

        if attempt < MAX_WEBHOOK_RETRIES:
            await asyncio.sleep(2 ** attempt)

    logger.error("Webhook failed after %d attempts", MAX_WEBHOOK_RETRIES)
    return False


@broker.subscriber(
    RabbitQueue(
        "payments.new",
        durable=True,
        arguments={"x-dead-letter-exchange": "payments.dlx"},
    ),
    retry=3,
)
async def handle_payment(message):
    payment_id = message.get("payment_id")
    webhook_url = message.get("webhook_url")

    if not payment_id:
        logger.error("Missing payment_id in message")
        return

    logger.info("Processing payment %s", payment_id)

    delay = random.uniform(2, 5)
    await asyncio.sleep(delay)

    is_success = random.random() < 0.9
    new_status = PaymentStatus.succeeded if is_success else PaymentStatus.failed

    async with async_session_factory() as session:
        result = await session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()

        if payment is None:
            logger.error("Payment %s not found in DB", payment_id)
            return

        payment.status = new_status
        payment.processed_at = datetime.utcnow()
        await session.commit()

    logger.info("Payment %s status updated to %s", payment_id, new_status.value)

    await send_webhook(webhook_url, {
        "payment_id": payment_id,
        "status": new_status.value,
        "processed_at": datetime.utcnow().isoformat(),
    })


@broker.subscriber(
    RabbitQueue("payments.dead", durable=True),
)
async def handle_dead_letter(message):
    logger.warning("Dead letter received: %s", message)
