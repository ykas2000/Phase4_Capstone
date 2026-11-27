# Changelog

## [0.3.0] - 2026-11-27 - CapstoneMongoDB (FastAPI + MongoDB)

### Steps 1-8: Core API
- Modular monolith layout: routes, service, repository and event layers.
- Pydantic models `DeviceCreate`, `DeviceResponse`, `StatusUpdate`, `AlertResponse`, with IPv4 validation via `ipaddress`.
- `InMemoryDeviceRepository` with instance-level storage that returns copies.
- `DeviceService` with `DeviceAlreadyExistsError` / `DeviceNotFoundError`; no HTTP concerns in the service.
- Six endpoints: `POST /devices` (201), `GET /devices`, `GET /devices/{device_id}`, `PATCH /devices/{device_id}/status`, `GET /alerts`, `GET /health`; errors mapped to 409/404.
- Offline alert rule: `create_offline_alert` fires only on a stored online -> offline transition.
- Swagger request examples and documented 404/409 responses.
- pytest service tests.

### Steps 9-13: MongoDB integration
- 9: `pymongo` + `python-dotenv`, `app/config.py`, `.env.example`, shared `MongoClient` with clean shutdown (`app/db/mongo.py`).
- 10: `app/db/collections.py` document shapes, serialization helpers and idempotent `ensure_indexes()` (unique `devices.device_id`, `alerts.device_id`, `alerts.timestamp`).
- 11: Indexes ensured at application startup, with mongosh/Python verification steps.
- 12: `MongoDeviceRepository` (DuplicateKeyError -> `DeviceAlreadyExistsError`, `_id` never exposed); `REPOSITORY_BACKEND=mongo|memory` selection.
- 13: Optional `location` field with backward-compatible reads; service tests run against both repositories using throwaway test databases.

### Docs
- Project documentation (DOCX) with checkpoint screenshots in `docs/`.
- Version indicator: `VERSION` file and `app.__version__` (shown in `/docs`).
