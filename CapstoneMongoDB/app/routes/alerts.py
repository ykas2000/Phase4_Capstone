from fastapi import APIRouter, Depends

from app.dependencies import get_device_service
from app.models import AlertResponse
from app.services.device_service import DeviceService

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
def list_alerts(service: DeviceService = Depends(get_device_service)):
    return service.list_alerts()
