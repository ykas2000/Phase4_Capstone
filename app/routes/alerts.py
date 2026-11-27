from fastapi import APIRouter, Depends

from app.models import AlertResponse
from app.repositories.device_repository import InMemoryDeviceRepository
from app.repositories.mysql_device_repository import MySqlDeviceRepository
from app.routes.dependencies import get_device_repository


router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[AlertResponse])
def list_alerts(
    repository: InMemoryDeviceRepository | MySqlDeviceRepository = Depends(get_device_repository),
) -> list[AlertResponse]:
    return repository.list_alerts()