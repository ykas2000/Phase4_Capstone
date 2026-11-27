from __future__ import annotations

from threading import Lock

from app.events import create_offline_alert
from app.models import AlertResponse, DeviceCreate, DeviceResponse, DeviceStatus
from app.repositories.device_repository import InMemoryDeviceRepository


class DeviceAlreadyExistsError(Exception):
    def __init__(self, device_id: str) -> None:
        super().__init__(f"Device '{device_id}' already exists")
        self.device_id = device_id


class DeviceNotFoundError(Exception):
    def __init__(self, device_id: str) -> None:
        super().__init__(f"Device '{device_id}' not found")
        self.device_id = device_id


class DeviceService:
    def __init__(self, repository: InMemoryDeviceRepository) -> None:
        self._repository = repository
        self._status_lock = Lock()

    def register(self, data: DeviceCreate) -> DeviceResponse:
        device = self._repository.add_device(data)
        if device is None:
            raise DeviceAlreadyExistsError(data.device_id)
        return device

    def list(self) -> list[DeviceResponse]:
        return self._repository.list_devices()

    def get(self, device_id: str) -> DeviceResponse:
        device = self._repository.get_device(device_id)
        if device is None:
            raise DeviceNotFoundError(device_id)
        return device

    def update_status(self, device_id: str, status: DeviceStatus) -> DeviceResponse:
        # Lock so concurrent updates can't both observe the online->offline transition.
        with self._status_lock:
            previous = self.get(device_id).status
            device = self._repository.update_status(device_id, status)
            if device is None:
                raise DeviceNotFoundError(device_id)
            if previous == DeviceStatus.online and device.status == DeviceStatus.offline:
                create_offline_alert(self._repository, device_id)
        return device

    def list_alerts(self) -> list[AlertResponse]:
        return self._repository.list_alerts()
