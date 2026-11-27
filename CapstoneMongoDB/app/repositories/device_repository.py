from threading import Lock

from app.models import AlertResponse, DeviceCreate, DeviceResponse, DeviceStatus


class InMemoryDeviceRepository:
    """Process-local storage: shared across requests, cleared on restart."""

    def __init__(self) -> None:
        self._devices: dict[str, DeviceResponse] = {}
        self._alerts: list[AlertResponse] = []
        self._lock = Lock()

    def add_device(self, data: DeviceCreate) -> DeviceResponse | None:
        with self._lock:
            if data.device_id in self._devices:
                return None
            device = DeviceResponse(**data.model_dump())
            self._devices[device.device_id] = device
            return device.model_copy()

    def list_devices(self) -> list[DeviceResponse]:
        with self._lock:
            return [device.model_copy() for device in self._devices.values()]

    def get_device(self, device_id: str) -> DeviceResponse | None:
        with self._lock:
            device = self._devices.get(device_id)
            return device.model_copy() if device else None

    def update_status(self, device_id: str, status: DeviceStatus) -> DeviceResponse | None:
        with self._lock:
            existing = self._devices.get(device_id)
            if existing is None:
                return None
            updated = existing.model_copy(update={"status": status})
            self._devices[device_id] = updated
            return updated.model_copy()

    def save_alert(self, alert: AlertResponse) -> AlertResponse:
        with self._lock:
            stored = alert.model_copy()
            self._alerts.append(stored)
            return stored.model_copy()

    def list_alerts(self) -> list[AlertResponse]:
        with self._lock:
            return [alert.model_copy() for alert in self._alerts]
