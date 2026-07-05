from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.outbox import OutboxRepository
from app.repositories.payment import PaymentRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.payments = PaymentRepository(session)
        self.outbox = OutboxRepository(session)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
