from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models import DeviceCreate, StatusUpdate
from app.repositories.mysql_device_repository import MySqlDeviceRepository
from app.services.device_service import DeviceAlreadyExistsError, DeviceService


@pytest.fixture
def mysql_session() -> Iterator[Session]:
    try:
        connection = engine.connect()
    except OperationalError:
        pytest.skip("MySQL is not reachable with the configured credentials")
    if not {"devices", "alerts"} <= set(inspect(connection).get_table_names()):
        connection.close()
        pytest.skip("Run 'alembic upgrade head' first")
    connection.rollback()

    # Repository commits only release savepoints; the outer transaction is always rolled back.
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def _payload(device_id: str, status: str = "online") -> DeviceCreate:
    return DeviceCreate(
        device_id=device_id, name="Test router", device_type="router",
        ip_address="10.0.0.1", status=status,
    )


def test_mysql_service_register_duplicate_and_single_offline_alert(mysql_session: Session) -> None:
    repository = MySqlDeviceRepository(mysql_session)
    service = DeviceService(repository)
    device_id = f"TEST-{uuid4().hex[:12]}"

    created = service.register(_payload(device_id))
    assert service.get(device_id) == created

    with pytest.raises(DeviceAlreadyExistsError):
        service.register(_payload(device_id))
    with pytest.raises(DeviceAlreadyExistsError):
        repository.add_device(_payload(device_id))

    service.update_status(device_id, StatusUpdate(status="offline"))
    service.update_status(device_id, StatusUpdate(status="offline"))

    alerts = [alert for alert in repository.list_alerts() if alert.device_id == device_id]
    assert len(alerts) == 1
    assert alerts[0].message == f"Device {device_id} went offline."
    assert service.get(device_id).status == "offline"


def test_mysql_offline_registration_creates_no_alert(mysql_session: Session) -> None:
    repository = MySqlDeviceRepository(mysql_session)
    service = DeviceService(repository)
    device_id = f"TEST-{uuid4().hex[:12]}"

    service.register(_payload(device_id, status="offline"))
    service.update_status(device_id, StatusUpdate(status="offline"))

    assert [alert for alert in repository.list_alerts() if alert.device_id == device_id] == []
