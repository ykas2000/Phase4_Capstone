# Changelog

All notable changes to NetPulse are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-11-27

MySQL persistence and Alembic migrations (Steps 9–13).

### Added
- **Database configuration (Step 9):** `app/config.py` reads MySQL settings and `DATABASE_URL` (`mysql+pymysql`) from environment variables or `.env`. `app/db/session.py` provides the SQLAlchemy engine, `SessionLocal`, `Base`, and a `get_db` dependency that closes sessions. A `.env.example` template was added.
- **ORM models (Step 10):** `devices` table (indexed primary key `device_id`, `name`, `device_type`, `ip_address`, `status`, `created_at`, `updated_at`) and `alerts` table (`id`, indexed foreign key `device_id`, `message`, `timestamp`), kept separate from the Pydantic API schemas.
- **Alembic (Step 11):** `alembic.ini` and `alembic/env.py` use `Base.metadata` and the URL from `app/config.py`. Migration `20261127_0001` creates the `devices` and `alerts` tables.
- **`MySqlDeviceRepository` (Step 12):** same methods as `InMemoryDeviceRepository`. It commits each write, rolls back on errors, translates MySQL duplicate-key errors (1062) into `DeviceAlreadyExistsError`, and returns Pydantic objects rather than ORM rows. `NETPULSE_STORAGE=memory|mysql` selects the repository per request.
- **Second migration (Step 13):** `20261127_0002` adds an optional `devices.location` column, with a reversible downgrade.
- **Tests:** repository tests with a mocked session, and MySQL integration tests that run in a rolled-back transaction (skipped when MySQL is unavailable). The suite has 16 tests.
- **Runbook:** `docs/RUNBOOK.md` covers setup, the five scenario checks, data reset, and troubleshooting.
- **Version indicator:** `app.__version__` (`0.2.0`), also reported in `/openapi.json` and `/docs`.

### Changed
- **Breaking:** `device_id` is now a string (letters, digits, `-`, `_`; maximum 50 characters), so IDs such as `RTR-101` are accepted. UUID strings remain valid.
- `MYSQL_DB` is accepted as an alias for `MYSQL_DATABASE`.

### Fixed
- Restored the package `__init__.py` files that were missing from the repository.

## [0.1.0] - 2026-11-26

Initial in-memory FastAPI modular monolith (Steps 1–8).

### Added
- **Project structure (Step 1):** route, service, repository, and event modules, plus `requirements.txt` (FastAPI, Uvicorn, Pydantic, pytest) and a README.
- **API schemas (Step 2):** `DeviceCreate`, `DeviceResponse`, `StatusUpdate`, and `AlertResponse`. Device type is limited to router, switch, or server; status is online or offline, defaulting to online; IPv4 addresses are validated with `ipaddress`.
- **`InMemoryDeviceRepository` (Step 3):** per-instance device dictionary and alert list that return copies, so callers cannot change stored data.
- **`DeviceService` (Step 4):** `register`, `list`, `get`, and `update_status`, raising `DeviceAlreadyExistsError` and `DeviceNotFoundError`.
- **Endpoints (Step 5):** `POST /devices` (201), `GET /devices`, `GET /devices/{device_id}`, `PATCH /devices/{device_id}/status`, `GET /alerts`, and `GET /health`. Routes map service errors to 409 and 404.
- **Offline alert rule (Step 6):** `create_offline_alert` records a UTC-timestamped alert through `repository.save_alert()`, only when a stored device changes from online to offline.
- **OpenAPI documentation (Step 7):** request examples for `DeviceCreate` and `StatusUpdate`, and documented 404 and 409 responses.
- **Service tests (Step 8):** fresh repository and service per test, covering registration, duplicate IDs, missing IDs, and the alert transition rules.

[0.2.0]: https://github.com/ykas2000/Phase4_Capstone/compare/819f9ca...v0.2.0
[0.1.0]: https://github.com/ykas2000/Phase4_Capstone/commit/819f9ca
