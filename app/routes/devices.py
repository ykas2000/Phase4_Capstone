from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.models import DeviceCreate, DeviceResponse, StatusUpdate
from app.routes.dependencies import get_device_service
from app.services.device_service import (
    DeviceAlreadyExistsError,
    DeviceNotFoundError,
    DeviceService,
)


router = APIRouter(prefix="/devices", tags=["devices"])


@router.post(
    "",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "A device with this ID already exists."}},
)
def create_device(payload: DeviceCreate, service: DeviceService = Depends(get_device_service)) -> DeviceResponse:
    try:
        return service.register(payload)
    except DeviceAlreadyExistsError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Device already exists") from error


@router.get("", response_model=List[DeviceResponse])
def list_devices(service: DeviceService = Depends(get_device_service)) -> List[DeviceResponse]:
    return service.list()


@router.get(
    "/{device_id}",
    response_model=DeviceResponse,
    responses={404: {"description": "Device not found."}},
)
def get_device(device_id: str, service: DeviceService = Depends(get_device_service)) -> DeviceResponse:
    try:
        return service.get(device_id)
    except DeviceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found") from error


@router.patch(
    "/{device_id}/status",
    response_model=DeviceResponse,
    responses={404: {"description": "Device not found."}},
)
def update_device_status(
    device_id: str, payload: StatusUpdate, service: DeviceService = Depends(get_device_service)
) -> DeviceResponse:
    try:
        return service.update_status(device_id, payload)
    except DeviceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found") from error