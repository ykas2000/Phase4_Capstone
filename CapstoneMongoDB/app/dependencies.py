from app.config import get_settings
from app.db.mongo import get_db
from app.repositories.device_repository import InMemoryDeviceRepository
from app.repositories.mongo_device_repository import MongoDeviceRepository
from app.services.device_service import DeviceService


def build_repository(backend: str) -> InMemoryDeviceRepository | MongoDeviceRepository:
    if backend == "mongo":
        return MongoDeviceRepository(get_db())
    if backend == "memory":
        return InMemoryDeviceRepository()
    raise ValueError(f"Unknown REPOSITORY_BACKEND '{backend}' (expected 'mongo' or 'memory')")


# Single process-wide repository shared by all routes.
repository = build_repository(get_settings().repository_backend)
device_service = DeviceService(repository)


def get_device_service() -> DeviceService:
    return device_service
