from contextlib import contextmanager
from datetime import timezone
from collections.abc import Iterator

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Alert, Device
from app.models import AlertResponse, DeviceCreate, DeviceResponse, StatusUpdate
from app.services.device_service import DeviceAlreadyExistsError


class MySqlDeviceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _device_response(device: Device) -> DeviceResponse:
        return DeviceResponse(
            device_id=device.device_id,
            name=device.name,
            device_type=device.device_type,
            ip_address=device.ip_address,
            status=device.status,
        )

    @staticmethod
    def _alert_response(alert: Alert) -> AlertResponse:
        timestamp = alert.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return AlertResponse(device_id=alert.device_id, message=alert.message, timestamp=timestamp)

    @contextmanager
    def _write(self) -> Iterator[None]:
        try:
            yield
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            if error.orig.args and error.orig.args[0] == 1062:
                raise DeviceAlreadyExistsError() from error
            raise
        except Exception:
            self._session.rollback()
            raise

    def add_device(self, payload: DeviceCreate) -> DeviceResponse:
        device = Device(**payload.model_dump())
        with self._write():
            self._session.add(device)
        return DeviceResponse(**payload.model_dump())

    def list_devices(self) -> list[DeviceResponse]:
        devices = self._session.scalars(select(Device).order_by(Device.created_at, Device.device_id))
        return [self._device_response(device) for device in devices]

    def get_device(self, device_id: str) -> DeviceResponse | None:
        device = self._session.get(Device, device_id)
        return self._device_response(device) if device is not None else None

    def update_status(self, device_id: str, update: StatusUpdate) -> DeviceResponse | None:
        with self._write():
            device = self._session.get(Device, device_id)
            if device is None:
                return None
            device.status = update.status
            response = self._device_response(device)
        return response

    def save_alert(self, alert: AlertResponse) -> AlertResponse:
        timestamp = alert.timestamp
        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
        with self._write():
            self._session.add(Alert(device_id=alert.device_id, message=alert.message, timestamp=timestamp))
        return alert.model_copy(deep=True)

    def list_alerts(self) -> list[AlertResponse]:
        alerts = self._session.scalars(select(Alert).order_by(Alert.id))
        return [self._alert_response(alert) for alert in alerts]

    def delete_device(self, device_id: str) -> DeviceResponse | None:
        with self._write():
            device = self._session.get(Device, device_id)
            if device is None:
                return None
            response = self._device_response(device)
            self._session.delete(device)
        return response