import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.outbox_publisher import start_outbox_publisher
from app.router import router

logging.basicConfig(level=logging.INFO)


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
