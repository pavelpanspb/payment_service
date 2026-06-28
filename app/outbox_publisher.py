import asyncio
import json
import logging
from datetime import datetime

import aio_pika
from sqlalchemy import select

from app.config import settings
from app.db import async_session_factory
from app.models import Outbox

logger = logging.getLogger("outbox_publisher")


async def publish_outbox_events():
    while True:
        try:
            connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            async with connection:
                channel = await connection.channel()
                exchange = await channel.declare_exchange(
                    "payments", aio_pika.ExchangeType.TOPIC, durable=True
                )

                async with async_session_factory() as session:
                    result = await session.execute(
                        select(Outbox)
                        .where(Outbox.processed_at.is_(None))
                        .order_by(Outbox.created_at)
                        .limit(50)
                    )
                    events = result.scalars().all()

                    for event in events:
                        try:
                            body = json.dumps(event.payload, default=str).encode()
                            await exchange.publish(
                                aio_pika.Message(
                                    body=body,
                                    content_type="application/json",
                                    message_id=str(event.id),
                                    headers={"event_type": event.event_type},
                                ),
                                routing_key="payment.created",
                            )
                            event.processed_at = datetime.utcnow()
                            await session.commit()
                            logger.info("Published outbox event %s", event.id)
                        except Exception as e:
                            await session.rollback()
                            event.retry_count = (event.retry_count or 0) + 1
                            event.last_error = str(e)
                            await session.commit()
                            logger.error("Failed to publish outbox event %s: %s", event.id, e)

        except Exception as e:
            logger.error("Outbox publisher connection error: %s", e)

        await asyncio.sleep(1)


async def start_outbox_publisher():
    task = asyncio.create_task(publish_outbox_events())
    logger.info("Outbox publisher started")
    return task
