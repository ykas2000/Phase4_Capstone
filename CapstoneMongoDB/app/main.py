import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db.collections import ensure_indexes
from app.db.mongo import close_client, get_db
from app.routes import alerts, devices, health

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        if get_settings().repository_backend == "mongo":
            # Fails startup if MongoDB is unreachable, so requests never hit a missing index.
            ensure_indexes(get_db())
            logger.info("MongoDB indexes ensured")
        yield
    finally:
        close_client()


app = FastAPI(title="NetPulse", lifespan=lifespan)
app.include_router(devices.router)
app.include_router(alerts.router)
app.include_router(health.router)
