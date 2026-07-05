import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Outbox


class OutboxRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, outbox: Outbox) -> None:
        self.session.add(outbox)

    async def get_unprocessed(self, limit: int = 50) -> list[Outbox]:
        result = await self.session.execute(
            select(Outbox)
            .where(Outbox.processed_at.is_(None))
            .order_by(Outbox.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result.scalars().all())

    async def mark_processed(self, event_id: uuid.UUID) -> None:
        await self.session.execute(
            update(Outbox)
            .where(Outbox.id == event_id)
            .values(processed_at=func.now())
        )

    async def mark_failed(self, event_id: uuid.UUID, error: str) -> None:
        await self.session.execute(
            update(Outbox)
            .where(Outbox.id == event_id)
            .values(
                retry_count=Outbox.retry_count + 1,
                last_error=error,
            )
        )
