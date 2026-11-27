import pytest

from app.models import DeviceCreate, DeviceStatus
from app.repositories.device_repository import InMemoryDeviceRepository
from app.repositories.mongo_device_repository import MongoDeviceRepository
from app.services.device_service import (
    DeviceAlreadyExistsError,
    DeviceNotFoundError,
    DeviceService,
)


@pytest.fixture(params=["memory", "mongo"])
def repository(request):
    if request.param == "memory":
        return InMemoryDeviceRepository()
    return MongoDeviceRepository(request.getfixturevalue("mongo_db"))


@pytest.fixture
def service(repository) -> DeviceService:
    return DeviceService(repository)


def make_device(device_id: str = "R1", status: DeviceStatus = DeviceStatus.online) -> DeviceCreate:
    return DeviceCreate(
        device_id=device_id,
        name="core-router",
        device_type="router",
        ip_address="10.0.0.1",
        status=status,
    )


def test_register_stores_device(service: DeviceService):
    created = service.register(make_device())

    assert created.device_id == "R1"
    assert created.status == DeviceStatus.online
    assert service.get("R1") == created
    assert service.list() == [created]


def test_register_duplicate_raises(service: DeviceService):
    service.register(make_device())

    with pytest.raises(DeviceAlreadyExistsError):
        service.register(make_device())


def test_get_missing_raises(service: DeviceService):
    with pytest.raises(DeviceNotFoundError):
        service.get("missing")


def test_update_status_missing_raises(service: DeviceService):
    with pytest.raises(DeviceNotFoundError):
        service.update_status("missing", DeviceStatus.offline)


def test_initial_offline_registration_creates_no_alert(service: DeviceService):
    service.register(make_device(status=DeviceStatus.offline))

    assert service.list_alerts() == []


def test_online_to_offline_creates_one_alert(service: DeviceService):
    service.register(make_device())

    updated = service.update_status("R1", DeviceStatus.offline)

    assert updated.status == DeviceStatus.offline
    alerts = service.list_alerts()
    assert len(alerts) == 1
    assert alerts[0].device_id == "R1"
    assert alerts[0].timestamp.utcoffset().total_seconds() == 0


def test_repeated_offline_keeps_single_alert(service: DeviceService):
    service.register(make_device())

    service.update_status("R1", DeviceStatus.offline)
    service.update_status("R1", DeviceStatus.offline)

    assert len(service.list_alerts()) == 1
