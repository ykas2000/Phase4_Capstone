from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.device_repository import InMemoryDeviceRepository
from app.repositories.mysql_device_repository import MySqlDeviceRepository
from app.services.device_service import DeviceService


def get_device_repository(
    request: Request, session: Session = Depends(get_db)
) -> InMemoryDeviceRepository | MySqlDeviceRepository:
    if request.app.state.storage == "mysql":
        return MySqlDeviceRepository(session)
    return request.app.state.device_repository


def get_device_service(
    repository: InMemoryDeviceRepository | MySqlDeviceRepository = Depends(get_device_repository),
) -> DeviceService:
    return DeviceService(repository)