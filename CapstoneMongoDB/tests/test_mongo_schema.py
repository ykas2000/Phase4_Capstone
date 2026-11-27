from unittest.mock import MagicMock

from app.db.collections import device_to_document, document_to_device, ensure_indexes
from app.models import DeviceCreate
from app.repositories.mongo_device_repository import MongoDeviceRepository

LEGACY_DOC = {
    "device_id": "OLD1",
    "name": "legacy-switch",
    "device_type": "switch",
    "ip_address": "10.0.0.50",
    "status": "online",
}


def test_legacy_document_without_location_reads_as_none():
    device = document_to_device({**LEGACY_DOC, "_id": "ignored"})

    assert device.location is None
    assert "_id" not in device.model_dump()


def test_location_round_trips():
    created = DeviceCreate(**{**LEGACY_DOC, "device_id": "NEW1"}, location="DC1 rack 4")

    doc = device_to_document(created)

    assert doc["location"] == "DC1 rack 4"
    assert document_to_device(doc).location == "DC1 rack 4"


def test_location_is_optional_on_create():
    assert device_to_document(DeviceCreate(**LEGACY_DOC))["location"] is None


def test_ensure_indexes_specs():
    collections = {"devices": MagicMock(), "alerts": MagicMock()}
    db = MagicMock()
    db.__getitem__.side_effect = collections.__getitem__

    ensure_indexes(db)

    collections["devices"].create_index.assert_called_once_with(
        [("device_id", 1)], unique=True, name="uniq_device_id"
    )
    alert_names = {c.kwargs["name"] for c in collections["alerts"].create_index.call_args_list}
    assert alert_names == {"alerts_device_id", "alerts_timestamp"}


# The tests below need a running MongoDB and are skipped otherwise.


def test_ensure_indexes_is_idempotent_on_mongo(mongo_db):
    ensure_indexes(mongo_db)

    device_indexes = mongo_db["devices"].index_information()
    assert device_indexes["uniq_device_id"]["unique"] is True
    assert {"alerts_device_id", "alerts_timestamp"} <= set(mongo_db["alerts"].index_information())


def test_mongo_reads_legacy_and_new_documents(mongo_db):
    mongo_db["devices"].insert_one(dict(LEGACY_DOC))
    repo = MongoDeviceRepository(mongo_db)
    repo.add_device(DeviceCreate(**{**LEGACY_DOC, "device_id": "NEW1"}, location="DC1"))

    by_id = {d.device_id: d for d in repo.list_devices()}

    assert by_id["OLD1"].location is None
    assert by_id["NEW1"].location == "DC1"
