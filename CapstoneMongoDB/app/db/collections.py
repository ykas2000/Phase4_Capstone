"""MongoDB document shapes and conversions; API models stay in app.models."""

from datetime import datetime, timezone
from typing import Any, NotRequired, TypedDict

from pymongo import ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database

from app.config import get_settings
from app.models import AlertResponse, DeviceCreate, DeviceResponse


class DeviceDocument(TypedDict):
    device_id: str
    name: str
    device_type: str
    ip_address: str
    status: str
    # Added later; documents written before this field existed lack it.
    location: NotRequired[str | None]


class AlertDocument(TypedDict):
    device_id: str
    message: str
    timestamp: datetime


def devices_collection(db: Database) -> Collection:
    return db[get_settings().devices_collection]


def alerts_collection(db: Database) -> Collection:
    return db[get_settings().alerts_collection]


def device_to_document(device: DeviceCreate | DeviceResponse) -> DeviceDocument:
    # mode="json" stores enums as their plain string values.
    data = device.model_dump(mode="json")
    return DeviceDocument(
        device_id=data["device_id"],
        name=data["name"],
        device_type=data["device_type"],
        ip_address=data["ip_address"],
        status=data["status"],
        location=data["location"],
    )


def document_to_device(doc: dict[str, Any]) -> DeviceResponse:
    return DeviceResponse(
        device_id=doc["device_id"],
        name=doc["name"],
        device_type=doc["device_type"],
        ip_address=doc["ip_address"],
        status=doc["status"],
        location=doc.get("location"),
    )


def alert_to_document(alert: AlertResponse) -> AlertDocument:
    return AlertDocument(
        device_id=alert.device_id,
        message=alert.message,
        timestamp=_as_utc(alert.timestamp),
    )


def document_to_alert(doc: dict[str, Any]) -> AlertResponse:
    return AlertResponse(
        device_id=doc["device_id"],
        message=doc["message"],
        timestamp=_as_utc(doc["timestamp"]),
    )


def _as_utc(value: datetime) -> datetime:
    # BSON dates are UTC; naive values come back when the client isn't tz_aware.
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def ensure_indexes(db: Database) -> None:
    """Create required indexes; safe to call repeatedly."""
    devices_collection(db).create_index(
        [("device_id", ASCENDING)], unique=True, name="uniq_device_id"
    )
    alerts = alerts_collection(db)
    alerts.create_index([("device_id", ASCENDING)], name="alerts_device_id")
    alerts.create_index([("timestamp", DESCENDING)], name="alerts_timestamp")
