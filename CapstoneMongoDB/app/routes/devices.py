from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_device_service
from app.models import DeviceCreate, DeviceResponse, ErrorResponse, StatusUpdate
from app.services.device_service import (
    DeviceAlreadyExistsError,
    DeviceNotFoundError,
    DeviceService,
)

router = APIRouter(prefix="/devices", tags=["devices"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Device not found"}}
CONFLICT = {409: {"model": ErrorResponse, "description": "Device ID already exists"}}


@router.get("", response_model=list[DeviceResponse])
def list_devices(service: DeviceService = Depends(get_device_service)):
    return service.list()


@router.get("/{device_id}", response_model=DeviceResponse, responses=NOT_FOUND)
def get_device(device_id: str, service: DeviceService = Depends(get_device_service)):
    try:
        return service.get(device_id)
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED, responses=CONFLICT
)
def create_device(data: DeviceCreate, service: DeviceService = Depends(get_device_service)):
    try:
        return service.register(data)
    except DeviceAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.patch("/{device_id}/status", response_model=DeviceResponse, responses=NOT_FOUND)
def update_status(
    device_id: str, data: StatusUpdate, service: DeviceService = Depends(get_device_service)
):
    try:
        return service.update_status(device_id, data.status)
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
