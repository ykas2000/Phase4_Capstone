import os

from fastapi import FastAPI

from app.repositories.device_repository import InMemoryDeviceRepository
from app.routes.alerts import router as alerts_router
from app.routes.devices import router as devices_router
from app.routes.health import router as health_router
from app.services.device_service import DeviceService


def create_app(storage: str | None = None) -> FastAPI:
    app = FastAPI(title="NetPulse API")
    app.state.storage = storage or os.getenv("NETPULSE_STORAGE", "memory").lower()
    if app.state.storage not in {"memory", "mysql"}:
        raise ValueError("NETPULSE_STORAGE must be 'memory' or 'mysql'")
    if app.state.storage == "memory":
        device_repository = InMemoryDeviceRepository()
        app.state.device_repository = device_repository
        app.state.device_service = DeviceService(device_repository)
    app.include_router(devices_router)
    app.include_router(alerts_router)
    app.include_router(health_router)
    return app


app = create_app()