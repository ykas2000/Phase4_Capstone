from pymongo import ASCENDING, ReturnDocument
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.db.collections import (
    alert_to_document,
    alerts_collection,
    device_to_document,
    devices_collection,
    document_to_alert,
    document_to_device,
)
from app.models import AlertResponse, DeviceCreate, DeviceResponse, DeviceStatus
from app.services.device_service import DeviceAlreadyExistsError

# Exclude Mongo's internal _id from every read.
_NO_ID = {"_id": False}


class MongoDeviceRepository:
    """MongoDB-backed storage with the same interface as InMemoryDeviceRepository."""

    def __init__(self, db: Database) -> None:
        self._devices = devices_collection(db)
        self._alerts = alerts_collection(db)

    def add_device(self, data: DeviceCreate) -> DeviceResponse:
        doc = device_to_document(data)
        try:
            # insert_one adds _id to the dict it is given, so pass a copy.
            self._devices.insert_one(dict(doc))
        except DuplicateKeyError:
            raise DeviceAlreadyExistsError(data.device_id)
        return document_to_device(doc)

    def list_devices(self) -> list[DeviceResponse]:
        cursor = self._devices.find({}, _NO_ID).sort("_id", ASCENDING)
        return [document_to_device(doc) for doc in cursor]

    def get_device(self, device_id: str) -> DeviceResponse | None:
        doc = self._devices.find_one({"device_id": device_id}, _NO_ID)
        return document_to_device(doc) if doc else None

    def update_status(self, device_id: str, status: DeviceStatus) -> DeviceResponse | None:
        doc = self._devices.find_one_and_update(
            {"device_id": device_id},
            {"$set": {"status": DeviceStatus(status).value}},
            projection=_NO_ID,
            return_document=ReturnDocument.AFTER,
        )
        return document_to_device(doc) if doc else None

    def save_alert(self, alert: AlertResponse) -> AlertResponse:
        doc = alert_to_document(alert)
        self._alerts.insert_one(dict(doc))
        return document_to_alert(doc)

    def list_alerts(self) -> list[AlertResponse]:
        cursor = self._alerts.find({}, _NO_ID).sort([("timestamp", ASCENDING), ("_id", ASCENDING)])
        return [document_to_alert(doc) for doc in cursor]
