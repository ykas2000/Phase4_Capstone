# NetPulse — Project Guide with Execution Screenshots

NetPulse is a FastAPI service for tracking network devices (routers, switches and servers). It records an alert whenever a device goes offline. Data is persisted in MySQL through SQLAlchemy, and the schema is versioned with Alembic migrations.

This guide describes the project and then walks through every step needed to set it up, run it, and verify it. Each step lists the exact commands, the expected result, and a screenshot of a real, successful run.

> **About the screenshots:** every terminal screenshot shows the real output of the listed commands, captured on the project VM (Ubuntu 24.04, Python 3.12, MySQL 8.0) from the `~/NetPulse` directory. The commands were executed and their exact output was rendered as a terminal window. Passwords in configuration output are masked. The Swagger screenshots are of the live API.

---

## Contents

- [1. Project overview](#1-project-overview)
- [2. Architecture](#2-architecture)
- [3. Technology stack](#3-technology-stack)
- [4. API endpoints](#4-api-endpoints)
- [5. Step-by-step execution](#5-step--by-step-execution)
  - [Step 1 — Environment check](#step-1--environment-check)
  - [Step 2 — Install dependencies](#step-2--install-dependencies)
  - [Step 3 — Project structure](#step-3--project-structure)
  - [Step 4 — Environment configuration](#step-4--environment-configuration)
  - [Step 5 — MySQL database and user](#step-5--mysql-database-and-user)
  - [Step 6 — Apply Alembic migrations](#step-6--apply-alembic-migrations)
  - [Step 7 — Verify tables in MySQL](#step-7--verify-tables-in-mysql)
  - [Step 8 — Migration downgrade and upgrade](#step-8--migration-downgrade-and-upgrade)
  - [Step 9 — Run the automated tests](#step-9--run-the-automated-tests)
  - [Step 10 — Start the API server](#step-10--start-the-api-server)
  - [Step 11 — Swagger UI and OpenAPI contract](#step-11--swagger-ui-and-openapi-contract)
  - [Step 12 — Register device RTR-101](#step-12--register-device-rtr-101)
  - [Step 13 — Set RTR-101 offline twice](#step-13--set-rtr-101-offline-twice)
  - [Step 14 — Check alerts: exactly one](#step-14--check-alerts-exactly-one)
  - [Step 15 — Data stored in MySQL](#step-15--data-stored-in-mysql)
  - [Step 16 — Data persists across a restart](#step-16--data-persists-across-a-restart)
  - [Step 17 — Release v0.2.0](#step-17--release-v020)
- [6. Acceptance checklist](#6-acceptance-checklist)
- [7. Resetting the demo data](#7-resetting-the-demo-data)
- [8. Troubleshooting](#8-troubleshooting)

---

## 1. Project overview

| Item | Value |
|---|---|
| Name | NetPulse API |
| Version | 0.2.0 (`app/__init__.py`, Git tag `v0.2.0`) |
| Repository | https://github.com/ykas2000/Phase4_Capstone |
| Purpose | Register network devices, update their online/offline status, and record an alert when a device goes offline |
| Storage | MySQL (`NETPULSE_STORAGE=mysql`), or in memory for isolated use (`NETPULSE_STORAGE=memory`, the default) |

**Business rules**

- `device_id` must be unique. Registering an existing ID returns **409 Conflict**.
- Reading or updating an unknown device returns **404 Not Found**.
- `device_type` must be `router`, `switch` or `server`. `status` must be `online` or `offline` and defaults to `online`.
- `ip_address` must be a valid **IPv4** address.
- `device_id` may contain only letters, digits, `-` and `_`, up to 50 characters (for example `RTR-101`).
- An alert is created **only** when a stored device changes from `online` to `offline`. Registering a device as offline creates no alert, and repeating an offline update creates no extra alert.

---

## 2. Architecture

NetPulse is a **modular monolith**: one deployable app split into layers, each with a single responsibility.

```mermaid
flowchart LR
    Client[Client / Swagger UI] --> Routes
    Routes[Routes<br/>app/routes/] --> Service[DeviceService<br/>app/services/]
    Service --> Repo{{Repository methods}}
    Service --> Events[Events<br/>app/events.py]
    Events --> Repo
    Repo --> Mem[InMemoryDeviceRepository]
    Repo --> SQL[MySqlDeviceRepository]
    SQL --> DB[(MySQL<br/>netpulse_db)]
    Alembic[Alembic migrations<br/>alembic/] --> DB
```

| Layer | Files | Responsibility |
|---|---|---|
| **Routes** | `app/routes/devices.py`, `alerts.py`, `health.py`, `dependencies.py` | HTTP only. Validate requests with Pydantic models, declare response models and status codes, and translate `DeviceAlreadyExistsError` → 409 and `DeviceNotFoundError` → 404. `dependencies.py` provides each request with a repository: the shared in-memory one, or a MySQL one bound to that request's database session. |
| **API schemas** | `app/models.py` | Pydantic models `DeviceCreate`, `DeviceResponse`, `StatusUpdate`, `AlertResponse` and `HealthResponse`, with validation and Swagger examples. |
| **Service** | `app/services/device_service.py` | Business rules, with no knowledge of HTTP or SQL: duplicate check, not-found errors, and the online-to-offline alert trigger. |
| **Repositories** | `app/repositories/device_repository.py`, `mysql_device_repository.py` | Storage behind the same methods: `add_device`, `list_devices`, `get_device`, `update_status`, `save_alert`, `list_alerts`. The MySQL version commits each write, rolls back on errors, maps MySQL duplicate-key error 1062 to `DeviceAlreadyExistsError`, and returns Pydantic objects rather than ORM rows. |
| **Events** | `app/events.py` | `create_offline_alert(repository, device_id)` builds a UTC-timestamped alert and saves it only through `repository.save_alert()`. |
| **Database** | `app/config.py`, `app/db/session.py`, `app/db/models.py` | Settings from `.env`, the SQLAlchemy engine, `SessionLocal`, the `get_db` dependency, and ORM tables (kept separate from the API schemas). |
| **Migrations** | `alembic.ini`, `alembic/env.py`, `alembic/versions/` | Versioned schema changes. `0001` creates `devices` and `alerts`; `0002` adds the optional `devices.location` column. |
| **Tests** | `tests/` | Service tests against an in-memory repository, repository tests with a mocked session, and real MySQL integration tests. |

Because the service depends only on the repository's methods, switching storage from memory to MySQL required **no** change to the business rules.

**Request flow for `PATCH /devices/RTR-101/status`**

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Route
    participant S as DeviceService
    participant P as MySqlDeviceRepository
    participant E as create_offline_alert
    participant D as MySQL
    C->>R: PATCH {"status":"offline"}
    R->>S: update_status("RTR-101", offline)
    S->>P: get_device("RTR-101")
    P->>D: SELECT
    S->>P: update_status(...)
    P->>D: UPDATE + COMMIT
    alt stored status was online
        S->>E: create_offline_alert(repo, "RTR-101")
        E->>P: save_alert(alert)
        P->>D: INSERT + COMMIT
    end
    R-->>C: 200 DeviceResponse
```

---

## 3. Technology stack

| Component | Version used | Role |
|---|---|---|
| Python | 3.12.3 | Runtime |
| FastAPI | 0.165.0 | Web framework and OpenAPI generation |
| Uvicorn | 0.54.0 | ASGI server |
| Pydantic | 2.14.4 | Request and response validation |
| SQLAlchemy | 2.1.9 | ORM and sessions |
| PyMySQL | 1.2.4 | MySQL driver (`mysql+pymysql`) |
| Alembic | 1.20.1 | Schema migrations |
| python-dotenv | 1.2.4 | Loads `.env` |
| pytest | 9.2.0 | Tests |
| MySQL | 8.0.46 | Database |

---

## 4. API endpoints

| Method | Path | Success | Errors | Description |
|---|---|---|---|---|
| POST | `/devices` | 201 | 409, 422 | Register a device |
| GET | `/devices` | 200 | — | List all devices |
| GET | `/devices/{device_id}` | 200 | 404, 422 | Get one device |
| PATCH | `/devices/{device_id}/status` | 200 | 404, 422 | Update status; online → offline creates an alert |
| GET | `/alerts` | 200 | — | List alerts |
| GET | `/health` | 200 | — | Returns `{"status":"ok"}` |

Interactive documentation is at `http://127.0.0.1:8000/docs`, and the raw contract at `http://127.0.0.1:8000/openapi.json`.

---

## 5. Step-by-step execution

Run every command from the project root. Activate the virtual environment first:

```bash
cd ~/NetPulse
source .venv/bin/activate
```

### Step 1 — Environment check

**Purpose:** confirm that Python, the virtual environment, the required packages, and the MySQL server are available.

```bash
python --version
which python
pip list | grep -iE '^(fastapi|uvicorn|pydantic|pytest|sqlalchemy|pymysql|alembic|python-dotenv) '
systemctl is-active mysql
mysql --version
```

**Expected result:** Python 3.12 from `.venv`, all eight packages listed, and MySQL reported as `active`.

![Step 1 - Environment check](screenshots/01_environment.png)

If MySQL is missing, install it with `sudo apt install mysql-server && sudo systemctl enable --now mysql`.

---

### Step 2 — Install dependencies

**Purpose:** install every Python dependency listed in `requirements.txt`.

```bash
cat requirements.txt
pip install -r requirements.txt
```

**Expected result:** each package reports `Requirement already satisfied` (or `Successfully installed` on a first install).

![Step 2 - Install dependencies](screenshots/02_install.png)

---

### Step 3 — Project structure

**Purpose:** show the modular layout: routes, services, repositories, events, database, migrations, tests and docs.

```bash
find . -path ./.venv -prune -o -path ./.git -prune -o -type f -name '*.py' -print | sort
```

**Expected result:** the files described in [Architecture](#2-architecture).

![Step 3 - Project structure](screenshots/03_structure.png)

---

### Step 4 — Environment configuration

**Purpose:** configure the storage mode and the MySQL connection through `.env`, which is git-ignored and never committed.

```bash
cp -n .env.example .env
nano .env
```

Required values:

```dotenv
NETPULSE_STORAGE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=netpulse_db
MYSQL_USER=netpulse_user
MYSQL_PASSWORD=YOUR_PASSWORD
DATABASE_URL=mysql+pymysql://netpulse_user:YOUR_PASSWORD@localhost:3306/netpulse_db
```

`DATABASE_URL`, when set, takes precedence over the individual `MYSQL_*` values. Verify the configuration:

```bash
git check-ignore -v .env
python -c 'from app.config import DATABASE_URL as u; print(u.drivername, u.host, u.port, u.database, u.username)'
```

**Expected result:** `.env` is ignored by `.gitignore`, and the app resolves the `mysql+pymysql` URL for `netpulse_db`. Passwords are masked in the screenshot.

![Step 4 - Environment configuration](screenshots/04_env_config.png)

---

### Step 5 — MySQL database and user

**Purpose:** create the `netpulse_db` database and the `netpulse_user` account, with privileges on that database only. This is a one-time setup; use the password from `.env`.

```bash
sudo mysql
```

```sql
CREATE DATABASE IF NOT EXISTS netpulse_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'netpulse_user'@'localhost' IDENTIFIED BY 'YOUR_PASSWORD';
GRANT ALL PRIVILEGES ON netpulse_db.* TO 'netpulse_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Verify:

```bash
sudo mysql -e "SHOW DATABASES LIKE 'netpulse%';"
sudo mysql -e "SELECT user, host FROM mysql.user WHERE user='netpulse_user';"
sudo mysql -e "SHOW GRANTS FOR 'netpulse_user'@'localhost';"
```

**Expected result:** the database and user exist, and the grant is limited to `netpulse_db.*`.

![Step 5 - MySQL database and user](screenshots/05_mysql_setup.png)

---

### Step 6 — Apply Alembic migrations

**Purpose:** create the schema with Alembic. The screenshot starts from an empty schema (`downgrade base`), then applies both revisions with `upgrade head`.

```bash
alembic downgrade base     # optional: start from an empty schema (deletes all data)
alembic upgrade head
alembic current
alembic history --verbose
```

**Expected result:** `Running upgrade -> 20261127_0001` and `Running upgrade 20261127_0001 -> 20261127_0002`; `alembic current` prints `20261127_0002 (head)`; the history shows both revisions.

![Step 6 - Apply Alembic migrations](screenshots/06_alembic_upgrade.png)

---

### Step 7 — Verify tables in MySQL

**Purpose:** confirm that the migrations created the expected tables, keys and foreign key.

```bash
sudo mysql -t netpulse_db -e 'SHOW TABLES;'
sudo mysql -t netpulse_db -e 'DESCRIBE devices;'
sudo mysql -t netpulse_db -e 'DESCRIBE alerts;'
```

**Expected result:**

- Tables `alembic_version`, `alerts` and `devices`.
- `devices.device_id` is a `varchar(50)` primary key, and `location` is nullable.
- `alerts.id` is an auto-increment primary key, and `alerts.device_id` is indexed (`MUL`) and references `devices.device_id` through foreign key `alerts_ibfk_1`.

![Step 7 - Tables created in MySQL](screenshots/07_mysql_tables.png)

---

### Step 8 — Migration downgrade and upgrade

**Purpose:** prove the second migration is reversible, and that the ORM models match the database.

```bash
alembic downgrade -1     # 0002 -> 0001: removes devices.location
alembic current
alembic upgrade head     # 0001 -> 0002: restores it
alembic current
alembic check            # compares ORM models with the live schema
```

**Expected result:** after the downgrade the `location` column count is `0`; after the upgrade the revision is back at `20261127_0002 (head)`; `alembic check` reports `No new upgrade operations detected.`

![Step 8 - Migration downgrade and upgrade](screenshots/08_alembic_reversible.png)

To create a migration for a future model change: `alembic revision --autogenerate -m "describe change"`, review the generated file, then run `alembic upgrade head`.

---

### Step 9 — Run the automated tests

**Purpose:** run all service, repository and MySQL persistence tests.

```bash
python -m pytest -q
python -m pytest -v
```

**Expected result:** `16 passed`.

![Step 9 - Automated tests](screenshots/09_pytest.png)

| Test file | Storage | Covers |
|---|---|---|
| `tests/test_device_service.py` | Fresh in-memory repository per test | Registration, `DeviceAlreadyExistsError`, `DeviceNotFoundError`, no alert on offline registration, one alert on online → offline, no extra alert on repeated offline, ID validation |
| `tests/test_mysql_device_repository.py` | Mocked SQLAlchemy session | Duplicate key (1062) → `DeviceAlreadyExistsError` with rollback, other integrity errors kept distinct, rollback on failed writes, plain objects returned instead of ORM rows, UTC timestamps, backend selection |
| `tests/test_mysql_integration.py` | **Real MySQL** | Service with the MySQL repository: duplicate IDs raise `DeviceAlreadyExistsError`; two offline updates record exactly one alert; offline registration records none |
| `tests/test_db_session.py` | None | `get_db` closes sessions; ORM tables compile for MySQL |

The MySQL integration tests run inside a transaction that is always rolled back, so they never change stored data. They are skipped, rather than failed, when MySQL is unreachable.

---

### Step 10 — Start the API server

**Purpose:** start NetPulse with MySQL storage.

```bash
uvicorn app.main:app --reload
```

In a **second terminal**, check that it is up:

```bash
curl http://127.0.0.1:8000/health
```

**Expected result:** `Uvicorn running on http://127.0.0.1:8000` and `Application startup complete.`; `/health` returns `{"status":"ok"}` with HTTP 200; the version is `0.2.0`.

![Step 10 - Start the API server](screenshots/10_start_server.png)

If port 8000 is already in use, stop the old server with `pkill -f "uvicorn app.main:app"`.

---

### Step 11 — Swagger UI and OpenAPI contract

**Purpose:** confirm that the six endpoints are documented, with request examples and 404/409 responses.

Open **http://127.0.0.1:8000/docs** in a browser.

**Expected result:** three groups (**devices**, **alerts**, **health**) containing the six endpoints, with the version shown as **0.2.0**.

![Step 11a - Swagger UI with six endpoints](screenshots/11a_swagger_overview.png)

Expanding **POST /devices** shows the `RTR-101` request example, and the responses list **201** and **409**:

![Step 11b - POST /devices example and 409 response](screenshots/11b_swagger_post_devices.png)

The same contract can be checked from the terminal:

```bash
python -c '
import json, urllib.request
s = json.load(urllib.request.urlopen("http://127.0.0.1:8000/openapi.json"))
ops = sorted((m.upper(), p) for p, ms in s["paths"].items() for m in ms)
for m, p in ops:
    print(m, p, sorted(s["paths"][p][m.lower()]["responses"]))
print("operations:", len(ops))
'
```

**Expected result:** 6 operations; `POST /devices` documents 201 and 409; `GET` and `PATCH` on `/devices/{device_id}` document 404; examples `RTR-101` and `{"status": "offline"}`.

![Step 11c - OpenAPI contract](screenshots/11_openapi_contract.png)

FastAPI generates `/openapi.json` from the route decorators (paths, methods, response models, status codes, `responses={404/409}`) and from the Pydantic models (schemas and examples). Swagger UI at `/docs` renders that document.

---

### Step 12 — Register device RTR-101

**Purpose:** register a device, and confirm that duplicates and invalid input are rejected.

```bash
B=http://127.0.0.1:8000; J='Content-Type: application/json'

curl -X POST $B/devices -H "$J" \
  -d '{"device_id":"RTR-101","name":"Core router","device_type":"router","ip_address":"192.168.1.1"}'   # 201
curl -X POST $B/devices -H "$J" \
  -d '{"device_id":"RTR-101","name":"Core router","device_type":"router","ip_address":"192.168.1.1"}'   # 409
curl -X POST $B/devices -H "$J" \
  -d '{"device_id":"RTR-999","name":"Bad","device_type":"router","ip_address":"999.1.1.1"}'            # 422
curl -X POST $B/devices -H "$J" \
  -d '{"device_id":"FW-1","name":"Bad","device_type":"firewall","ip_address":"10.0.0.1"}'              # 422
curl $B/devices
```

**Expected result:** **201** with `"status":"online"` (the default); **409** `Device already exists`; **422** for an invalid IPv4 address and for an invalid device type.

![Step 12 - Register RTR-101](screenshots/12_register_device.png)

---

### Step 13 — Set RTR-101 offline twice

**Purpose:** send the same offline update twice, and confirm that unknown devices return 404.

```bash
curl -X PATCH $B/devices/RTR-101/status -H "$J" -d '{"status":"offline"}'   # 200, creates the alert
curl -X PATCH $B/devices/RTR-101/status -H "$J" -d '{"status":"offline"}'   # 200, no new alert
curl $B/devices/NOPE-1                                                      # 404
curl -X PATCH $B/devices/NOPE-1/status -H "$J" -d '{"status":"offline"}'    # 404
```

**Expected result:** both PATCH calls return **200** with `"status":"offline"`; the unknown device returns **404** `Device not found`.

![Step 13 - PATCH offline twice](screenshots/13_patch_offline.png)

---

### Step 14 — Check alerts: exactly one

**Purpose:** verify the alert rule: only the online → offline transition creates an alert.

```bash
curl $B/alerts
curl -s $B/alerts | python -c 'import json,sys; print(sum(a["device_id"]=="RTR-101" for a in json.load(sys.stdin)))'

# A device registered as offline must never create an alert
curl -X POST $B/devices -H "$J" \
  -d '{"device_id":"SW-201","name":"Lab switch","device_type":"switch","ip_address":"192.168.1.20","status":"offline"}'
curl -X PATCH $B/devices/SW-201/status -H "$J" -d '{"status":"offline"}'
curl $B/alerts
```

**Expected result:** exactly **1** alert, `Device RTR-101 went offline.`, with a UTC timestamp (`...Z`). `SW-201` has **0** alerts, and the total stays at 1.

![Step 14 - Exactly one alert](screenshots/14_alerts.png)

---

### Step 15 — Data stored in MySQL

**Purpose:** confirm the data is written to MySQL, not held in memory.

```bash
sudo mysql -t netpulse_db -e 'SELECT device_id, name, device_type, ip_address, status, created_at, updated_at FROM devices;'
sudo mysql -t netpulse_db -e 'SELECT id, device_id, message, timestamp FROM alerts;'
```

**Expected result:** `RTR-101` and `SW-201` with status `offline`, and a single alert row for `RTR-101`.

![Step 15 - Data stored in MySQL](screenshots/15_mysql_rows.png)

> The alert `id` is not necessarily `1`. MySQL never reuses auto-increment numbers, including those used by the rolled-back integration tests in Step 9.

---

### Step 16 — Data persists across a restart

**Purpose:** prove persistence by stopping the server, confirming it is down, restarting it, and reading the data again.

```bash
pkill -f "uvicorn app.main:app"       # or Ctrl+C in the server terminal
curl $B/health                        # fails: server is down
uvicorn app.main:app --reload         # start again
curl $B/devices/RTR-101
curl $B/alerts
```

**Expected result:** while the server is down the connection is refused; after the restart, `RTR-101` is still `offline` and the same single alert is returned.

![Step 16 - Data persists across restart](screenshots/16_persistence_restart.png)

---

### Step 17 — Release v0.2.0

**Purpose:** show the release metadata: the version indicator, the annotated tag, the changelog, and confirmation that no secrets are tracked.

```bash
python -c 'from app import __version__; print(__version__)'
git tag -n1 -l v0.2.0
git log --oneline --decorate -n 4
head -5 CHANGELOG.md
git ls-files | grep -E '(^|/)\.env$' || echo '.env is not tracked (good)'
```

**Expected result:** version `0.2.0`; tag `v0.2.0` on the release commit; `CHANGELOG.md` contains the 0.2.0 entry; `.env` is not tracked.

![Step 17 - Release v0.2.0](screenshots/17_release.png)

---

## 6. Acceptance checklist

| # | Check | Evidence | Result |
|---|---|---|---|
| 1 | Swagger and OpenAPI: six endpoints, request examples, documented 404/409 | Step 11 | Passed |
| 2 | Offline alert rule: `RTR-101` → 201, offline twice, `GET /alerts` → exactly 1 | Steps 12–14 | Passed |
| 3 | Alembic and MySQL: `upgrade head` applies cleanly, tables exist, data persists across restarts | Steps 6–8, 15–16 | Passed |
| 4 | Automated tests: `python -m pytest -q` passes | Step 9 | 16 passed |
| 5 | Architecture: route, service, repository, event and migration responsibilities | [Section 2](#2-architecture) | Documented |

---

## 7. Resetting the demo data

To repeat Steps 12–16 with `RTR-101`, clear the data first. **This deletes all devices and alerts.**

```bash
sudo mysql netpulse_db -e "DELETE FROM alerts; DELETE FROM devices;"
```

Alternatively, rebuild the schema with `alembic downgrade base && alembic upgrade head`.

To keep a backup before resetting:

```bash
sudo mysqldump --no-tablespaces netpulse_db > ~/netpulse_db_backup.sql
# restore later with: sudo mysql netpulse_db < ~/netpulse_db_backup.sql
```

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Can't connect to MySQL server ... (111 Connection refused)` | MySQL is not running | `sudo systemctl enable --now mysql` |
| `(1045, "Access denied for user ...")` | The MySQL user is missing, or its password differs from `.env` | Repeat [Step 5](#step-5--mysql-database-and-user) with the password from `.env` |
| `(1049, "Unknown database ...")` | The database has not been created | [Step 5](#step-5--mysql-database-and-user) |
| `Table 'netpulse_db.devices' doesn't exist` | Migrations have not been applied | `alembic upgrade head` |
| Data disappears after a restart | Memory storage is in use | Set `NETPULSE_STORAGE=mysql` in `.env`, then restart |
| 409 when registering `RTR-101` | The device already exists | Use a new ID or [reset the data](#7-resetting-the-demo-data) |
| 422 on `POST /devices` | Invalid IP address, type, status or ID format | See the [business rules](#1-project-overview) |
| `[Errno 98] address already in use` | An old server is still running on port 8000 | `pkill -f "uvicorn app.main:app"` |
| `/docs` is blank | The Swagger UI CDN is unreachable | Check internet access; `/openapi.json` works offline |
| `Command 'python' not found` | The virtual environment is not active | `source .venv/bin/activate` |
| `python -m pytest` shows 2 skipped | MySQL is unreachable or not migrated | Fix the connection, run `alembic upgrade head`, then `python -m pytest -q -rs` |

For more detail, see [RUNBOOK.md](RUNBOOK.md) and [../CHANGELOG.md](../CHANGELOG.md).
