import asyncio
import json
import logging

import aio_pika

from app.config import settings
from app.db import async_session_factory
from app.repositories.outbox import OutboxRepository

logger = logging.getLogger("outbox_publisher")


class OutboxPublisher:
    def __init__(self):
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.Channel | None = None
        self._exchange: aio_pika.Exchange | None = None

    async def start(self) -> None:
        self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            "payments", aio_pika.ExchangeType.TOPIC, durable=True
        )
        logger.info("Connected to RabbitMQ")

    async def stop(self) -> None:
        if self._connection:
            await self._connection.close()
            logger.info("Disconnected from RabbitMQ")

    async def run_forever(self) -> None:
        await self.start()
        try:
            while True:
                await self._publish_batch()
                await asyncio.sleep(settings.outbox_poll_interval)
        finally:
            await self.stop()

    async def _publish_batch(self) -> None:
        async with async_session_factory() as session:
            repo = OutboxRepository(session)
            events = await repo.get_unprocessed(settings.outbox_batch_size)

            for event in events:
                try:
                    body = json.dumps(event.payload, default=str).encode()
                    await self._exchange.publish(
                        aio_pika.Message(
                            body=body,
                            content_type="application/json",
                            message_id=str(event.id),
                            headers={"event_type": event.event_type},
                        ),
                        routing_key="payment.created",
                    )
                    await repo.mark_processed(event.id)
                    logger.info("Published outbox event %s", event.id)
                except Exception as e:
                    await repo.mark_failed(event.id, str(e))
                    logger.error("Failed to publish outbox event %s: %s", event.id, e)

            await session.commit()

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and not self._connection.is_closed


async def start_outbox_publisher() -> asyncio.Task:
    publisher = OutboxPublisher()
    task = asyncio.create_task(publisher.run_forever())
    logger.info("Outbox publisher task started")
    return task
