from datetime import timezone

import pytest

from app.models import DeviceCreate, StatusUpdate
from app.repositories.device_repository import InMemoryDeviceRepository
from app.services.device_service import (
    DeviceAlreadyExistsError,
    DeviceNotFoundError,
    DeviceService,
)


@pytest.fixture
def service_context() -> tuple[InMemoryDeviceRepository, DeviceService]:
    repository = InMemoryDeviceRepository()
    return repository, DeviceService(repository)


def test_device_lifecycle(
    service_context: tuple[InMemoryDeviceRepository, DeviceService],
) -> None:
    _, service = service_context
    device = service.register(
        DeviceCreate(name="router", device_type="router", ip_address="192.168.1.1")
    )

    assert service.get(device.device_id) == device
    assert service.list() == [device]

    service.delete_device(device.device_id)

    assert service.list() == []


def test_register_rejects_duplicate_id(
    service_context: tuple[InMemoryDeviceRepository, DeviceService],
) -> None:
    _, service = service_context
    device_id = "RTR-101"
    payload = DeviceCreate(
        device_id=device_id,
        name="router",
        device_type="router",
        ip_address="192.168.1.1",
    )

    service.register(payload)

    with pytest.raises(DeviceAlreadyExistsError):
        service.register(payload)

    assert service.get(device_id).name == "router"
    assert len(service.list()) == 1


def test_missing_device_raises_not_found(
    service_context: tuple[InMemoryDeviceRepository, DeviceService],
) -> None:
    _, service = service_context

    with pytest.raises(DeviceNotFoundError):
        service.get("MISSING-1")


def test_device_id_rejects_invalid_characters() -> None:
    with pytest.raises(ValueError):
        DeviceCreate(
            device_id="RTR 101/../", name="router", device_type="router", ip_address="192.168.1.1"
        )


def test_offline_alert_only_fires_on_online_to_offline(
    service_context: tuple[InMemoryDeviceRepository, DeviceService],
) -> None:
    repository, service = service_context
    offline_device = service.register(
        DeviceCreate(
            name="switch",
            device_type="switch",
            ip_address="192.168.1.2",
            status="offline",
        )
    )
    assert repository.list_alerts() == []

    online_device = service.register(
        DeviceCreate(name="server", device_type="server", ip_address="192.168.1.3")
    )
    service.update_status(online_device.device_id, StatusUpdate(status="offline"))
    alerts = repository.list_alerts()

    assert len(alerts) == 1
    assert alerts[0].device_id == online_device.device_id
    assert alerts[0].message == f"Device {online_device.device_id} went offline."
    assert alerts[0].timestamp.tzinfo == timezone.utc

    service.update_status(online_device.device_id, StatusUpdate(status="offline"))

    assert repository.list_alerts() == alerts
    assert service.get(offline_device.device_id).status == "offline"

    service.update_status(online_device.device_id, StatusUpdate(status="online"))
    service.update_status(online_device.device_id, StatusUpdate(status="offline"))
    assert len(repository.list_alerts()) == 2