from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import IntegrityError
from starlette.requests import Request

from app.db.models import Alert, Device
from app.main import create_app
from app.models import AlertResponse, DeviceCreate, StatusUpdate
from app.repositories.device_repository import InMemoryDeviceRepository
from app.repositories.mysql_device_repository import MySqlDeviceRepository
from app.routes.dependencies import get_device_repository, get_device_service
from app.services.device_service import DeviceAlreadyExistsError


def test_duplicate_device_rolls_back() -> None:
    session = Mock()
    session.commit.side_effect = IntegrityError(None, None, Exception(1062, "Duplicate entry"))
    repository = MySqlDeviceRepository(session)

    with pytest.raises(DeviceAlreadyExistsError):
        repository.add_device(DeviceCreate(name="router", device_type="router", ip_address="192.168.1.1"))

    session.rollback.assert_called_once_with()


def test_other_integrity_errors_are_not_reported_as_duplicates() -> None:
    session = Mock()
    session.commit.side_effect = IntegrityError(None, None, Exception(1452, "Foreign key violation"))
    repository = MySqlDeviceRepository(session)

    with pytest.raises(IntegrityError):
        repository.add_device(DeviceCreate(name="router", device_type="router", ip_address="192.168.1.1"))

    session.rollback.assert_called_once_with()


def test_staging_failure_rolls_back() -> None:
    session = Mock()
    session.add.side_effect = RuntimeError("could not stage device")
    repository = MySqlDeviceRepository(session)

    with pytest.raises(RuntimeError):
        repository.add_device(DeviceCreate(name="router", device_type="router", ip_address="192.168.1.1"))

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()


def test_repository_returns_detached_models_for_devices() -> None:
    session = Mock()
    device_id = "RTR-101"
    device = Device(
        device_id=device_id, name="router", device_type="router",
        ip_address="192.168.1.1", status="online"
    )
    session.get.return_value = device
    session.scalars.return_value = [device]
    repository = MySqlDeviceRepository(session)

    retrieved = repository.get_device(device_id)
    assert retrieved is not None
    retrieved.name = "changed"
    assert device.name == "router"
    assert repository.list_devices()[0].device_id == device_id
    updated = repository.update_status(device_id, StatusUpdate(status="offline"))
    assert updated is not None and updated.status == "offline"
    session.commit.assert_called_once_with()


def test_alerts_are_saved_as_utc_and_returned_as_domain_objects() -> None:
    session = Mock()
    device_id = "SRV-201"
    timestamp = datetime(2026, 1, 1, 12, tzinfo=timezone(timedelta(hours=2)))
    alert = AlertResponse(device_id=device_id, message="Device offline", timestamp=timestamp)
    repository = MySqlDeviceRepository(session)

    saved = repository.save_alert(alert)
    row = session.add.call_args.args[0]
    assert row.timestamp == datetime(2026, 1, 1, 10)
    assert saved is not alert
    session.scalars.return_value = [row]
    listed = repository.list_alerts()
    assert listed[0].timestamp == datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
    assert isinstance(row, Alert)
    session.commit.assert_called_once_with()


@pytest.mark.parametrize("storage", ["memory", "mysql"])
def test_backend_selection_uses_shared_memory_or_request_session(storage: str) -> None:
    app = create_app(storage)
    request = Request({"type": "http", "app": app})
    session = Mock()

    repository = get_device_repository(request, session)
    service = get_device_service(repository)

    if storage == "memory":
        assert isinstance(repository, InMemoryDeviceRepository)
        assert repository is app.state.device_repository
    else:
        assert isinstance(repository, MySqlDeviceRepository)
        assert repository._session is session
    assert service._repository is repository