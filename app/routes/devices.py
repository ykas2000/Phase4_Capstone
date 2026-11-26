from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.models import DeviceCreate, DeviceResponse, StatusUpdate
from app.services.device_service import (
    DeviceAlreadyExistsError,
    DeviceNotFoundError,
    DeviceService,
)


router = APIRouter(prefix="/devices", tags=["devices"])


def get_device_service(request: Request) -> DeviceService:
    return request.app.state.device_service


@router.post(
    "",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "A device with this ID already exists."}},
)
def create_device(payload: DeviceCreate, request: Request) -> DeviceResponse:
    try:
        return get_device_service(request).register(payload)
    except DeviceAlreadyExistsError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Device already exists") from error


@router.get("", response_model=List[DeviceResponse])
def list_devices(request: Request) -> List[DeviceResponse]:
    return get_device_service(request).list()


@router.get(
    "/{device_id}",
    response_model=DeviceResponse,
    responses={404: {"description": "Device not found."}},
)
def get_device(device_id: UUID, request: Request) -> DeviceResponse:
    try:
        return get_device_service(request).get(device_id)
    except DeviceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found") from error


@router.patch(
    "/{device_id}/status",
    response_model=DeviceResponse,
    responses={404: {"description": "Device not found."}},
)
def update_device_status(
    device_id: UUID, payload: StatusUpdate, request: Request
) -> DeviceResponse:
    try:
        return get_device_service(request).update_status(device_id, payload)
    except DeviceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found") from error