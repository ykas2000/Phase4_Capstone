from typing import Dict, List, Optional

from app.models import AlertResponse, DeviceCreate, DeviceResponse, StatusUpdate


class InMemoryDeviceRepository:
    def __init__(self) -> None:
        self._devices: Dict[str, DeviceResponse] = {}
        self._alerts: List[AlertResponse] = []

    def add_device(self, payload: DeviceCreate) -> DeviceResponse:
        device = DeviceResponse(**payload.model_dump())
        self._devices[device.device_id] = device
        return device.model_copy(deep=True)

    def list_devices(self) -> List[DeviceResponse]:
        return [device.model_copy(deep=True) for device in self._devices.values()]

    def get_device(self, device_id: str) -> Optional[DeviceResponse]:
        device = self._devices.get(device_id)
        return device.model_copy(deep=True) if device is not None else None

    def update_status(
        self, device_id: str, update: StatusUpdate
    ) -> Optional[DeviceResponse]:
        device = self._devices.get(device_id)
        if device is None:
            return None
        device.status = update.status
        return device.model_copy(deep=True)

    def save_alert(self, alert: AlertResponse) -> AlertResponse:
        stored_alert = alert.model_copy(deep=True)
        self._alerts.append(stored_alert)
        return stored_alert.model_copy(deep=True)

    def list_alerts(self) -> List[AlertResponse]:
        return [alert.model_copy(deep=True) for alert in self._alerts]

    def delete_device(self, device_id: str) -> Optional[DeviceResponse]:
        device = self._devices.pop(device_id, None)
        return device.model_copy(deep=True) if device is not None else None