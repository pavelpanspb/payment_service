import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.logging_conf import setup_logging
from app.outbox_publisher import start_outbox_publisher
from app.router import router

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = await start_outbox_publisher()
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Payment Processing Service", lifespan=lifespan)
app.include_router(router)
