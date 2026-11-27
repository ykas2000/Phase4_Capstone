from unittest.mock import Mock

from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from app.db.models import Alert, Device
from app.db import session


def test_get_db_closes_session(monkeypatch) -> None:
    db = Mock()
    monkeypatch.setattr(session, "SessionLocal", lambda: db)
    dependency = session.get_db()

    assert next(dependency) is db
    dependency.close()

    db.close.assert_called_once_with()


def test_orm_tables_compile_for_mysql() -> None:
    devices = Device.__table__
    alerts = Alert.__table__

    assert set(devices.columns.keys()) == {
        "device_id", "name", "device_type", "ip_address", "status", "location", "created_at", "updated_at"
    }
    assert devices.c.device_id.primary_key
    assert devices.c.location.nullable
    assert any("device_id" in index.columns for index in devices.indexes)
    assert set(alerts.columns.keys()) == {"id", "device_id", "message", "timestamp"}
    assert alerts.c.id.primary_key
    assert any(key.target_fullname == "devices.device_id" for key in alerts.c.device_id.foreign_keys)
    assert "CREATE TABLE devices" in str(CreateTable(devices).compile(dialect=mysql.dialect()))
    assert "CREATE TABLE alerts" in str(CreateTable(alerts).compile(dialect=mysql.dialect()))