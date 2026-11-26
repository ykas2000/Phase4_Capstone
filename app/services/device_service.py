from uuid import UUID

from app.events import create_offline_alert
from app.models import DeviceCreate, DeviceResponse, StatusUpdate
from app.repositories.device_repository import InMemoryDeviceRepository


class DeviceAlreadyExistsError(Exception):
    pass


class DeviceNotFoundError(Exception):
    pass


class DeviceService:
    def __init__(self, repository: InMemoryDeviceRepository) -> None:
        self._repository = repository

    def register(self, payload: DeviceCreate) -> DeviceResponse:
        if self._repository.get_device(payload.device_id) is not None:
            raise DeviceAlreadyExistsError(payload.device_id)
        return self._repository.add_device(payload)

    def list(self) -> list[DeviceResponse]:
        return self._repository.list_devices()

    def get(self, device_id: UUID) -> DeviceResponse:
        device = self._repository.get_device(device_id)
        if device is None:
            raise DeviceNotFoundError(device_id)
        return device

    def update_status(self, device_id: UUID, update: StatusUpdate) -> DeviceResponse:
        device = self._repository.get_device(device_id)
        if device is None:
            raise DeviceNotFoundError(device_id)

        transitioned_offline = device.status == "online" and update.status == "offline"
        updated_device = self._repository.update_status(device_id, update)
        if updated_device is None:
            raise DeviceNotFoundError(device_id)
        if transitioned_offline:
            create_offline_alert(self._repository, device_id)
        return updated_device

    def delete_device(self, device_id: UUID) -> None:
        device = self._repository.delete_device(device_id)
        if device is None:
            raise DeviceNotFoundError(device_id)