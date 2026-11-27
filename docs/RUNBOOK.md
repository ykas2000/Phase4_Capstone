# NetPulse Runbook

How to set up, run, and verify the NetPulse FastAPI + MySQL project. Every command runs from the project root (`~/NetPulse`) unless stated otherwise.

## Contents

1. [Prerequisites](#1-prerequisites)
2. [One-time setup](#2-one-time-setup)
3. [Start the API](#3-start-the-api)
4. [Scenario checks](#4-scenario-checks)
   - [Check 1: Swagger and OpenAPI contract](#check-1-swagger-and-openapi-contract)
   - [Check 2: Offline transition alert rule](#check-2-offline-transition-alert-rule)
   - [Check 3: Alembic and MySQL persistence](#check-3-alembic-and-mysql-persistence)
   - [Check 4: Automated tests](#check-4-automated-tests)
   - [Check 5: Architecture explanation](#check-5-architecture-explanation)
5. [Resetting data](#5-resetting-data)
6. [Troubleshooting](#6-troubleshooting)
7. [Command quick reference](#7-command-quick-reference)

---

## 1. Prerequisites

| Requirement | Check with |
|---|---|
| Python 3.12 with the project virtual environment in `.venv/` | `ls .venv/bin/python` |
| MySQL 8 server installed and running | `systemctl is-active mysql` → `active` |
| `curl` for API checks | `curl --version` |

If MySQL is not installed:

```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl enable --now mysql
```

---

## 2. One-time setup

### 2.1 Install Python dependencies

```bash
cd ~/NetPulse
source .venv/bin/activate
pip install -r requirements.txt
```

### 2.2 Configure `.env`

```bash
cp -n .env.example .env
nano .env
```

`.env` must contain the following values. Replace `YOUR_PASSWORD` with your own password:

```dotenv
NETPULSE_STORAGE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=netpulse_db
MYSQL_USER=netpulse_user
MYSQL_PASSWORD=YOUR_PASSWORD
DATABASE_URL=mysql+pymysql://netpulse_user:YOUR_PASSWORD@localhost:3306/netpulse_db
```

Notes:

- `NETPULSE_STORAGE=mysql` makes the API persist data in MySQL. If it is unset or set to `memory`, data is kept in memory and lost on restart.
- When `DATABASE_URL` is set, it takes precedence over the individual `MYSQL_*` values. Keep the two consistent.
- If the password contains special characters such as `@`, `:`, `/` or `#`, URL-encode them in `DATABASE_URL`.
- `.env` is listed in `.gitignore`. Never commit it.

### 2.3 Create the MySQL database and user

Use the same password as in `.env`:

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

### 2.4 Apply migrations

```bash
alembic upgrade head
alembic current
```

Expected output:

```text
20261127_0002 (head)
```

---

## 3. Start the API

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Expected output:

```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

| URL | Purpose |
|---|---|
| http://127.0.0.1:8000/docs | Swagger UI |
| http://127.0.0.1:8000/openapi.json | Raw OpenAPI contract |
| http://127.0.0.1:8000/health | Health check |

Leave this terminal running and open a **second terminal** for the checks below. In that terminal, set these helper variables once:

```bash
cd ~/NetPulse
source .venv/bin/activate
B=http://127.0.0.1:8000
J='Content-Type: application/json'
```

If port 8000 is already in use, stop the old server first:

```bash
pkill -f "uvicorn app.main:app"
```

---

## 4. Scenario checks

### Check 1: Swagger and OpenAPI contract

**Goal:** six endpoints are visible in `/docs`, with request examples and documented 404/409 responses.

#### Expected endpoints

| Method | Path | Success | Documented errors |
|---|---|---|---|
| POST | `/devices` | 201 | 409 (device already exists), 422 |
| GET | `/devices` | 200 | — |
| GET | `/devices/{device_id}` | 200 | 404 (device not found), 422 |
| PATCH | `/devices/{device_id}/status` | 200 | 404 (device not found), 422 |
| GET | `/alerts` | 200 | — |
| GET | `/health` | 200 | — |

#### Steps in the browser

1. Open http://127.0.0.1:8000/docs.
2. Confirm three groups, **devices**, **alerts** and **health**, containing the six endpoints above.
3. Expand **POST /devices**. The request body example shows:

   ```json
   {
     "device_id": "RTR-101",
     "name": "Core router",
     "device_type": "router",
     "ip_address": "192.168.1.1",
     "status": "online"
   }
   ```

   The **Responses** section lists **201** and **409**.
4. Expand **PATCH /devices/{device_id}/status**. The example body is `{"status": "offline"}`, and the responses list **200** and **404**.
5. Expand **GET /devices/{device_id}**. The responses list **200** and **404**.

#### Check from the command line

```bash
python -c '
import json, urllib.request
s = json.load(urllib.request.urlopen("http://127.0.0.1:8000/openapi.json"))
ops = sorted((m.upper(), p) for p, ms in s["paths"].items() for m in ms)
for m, p in ops:
    codes = sorted(s["paths"][p][m.lower()]["responses"])
    print(f"{m:6} {p:30} responses={codes}")
print("operations:", len(ops))
c = s["components"]["schemas"]
print("DeviceCreate example:", c["DeviceCreate"]["examples"][0])
print("StatusUpdate example:", c["StatusUpdate"]["examples"][0])
'
```

Expected output:

```text
GET    /alerts                        responses=['200']
GET    /devices                       responses=['200']
GET    /devices/{device_id}           responses=['200', '404', '422']
GET    /health                        responses=['200']
PATCH  /devices/{device_id}/status    responses=['200', '404', '422']
POST   /devices                       responses=['201', '409', '422']
operations: 6
DeviceCreate example: {'device_id': 'RTR-101', ...}
StatusUpdate example: {'status': 'offline'}
```

#### How it works

FastAPI builds `/openapi.json` from the route decorators (paths, methods, `response_model`, `status_code`, `responses={404/409}`) and from the Pydantic models in `app/models.py` (request and response schemas, plus `json_schema_extra` examples). `/docs` renders that document with Swagger UI.

> Swagger UI loads its JavaScript and CSS from a CDN. If `/docs` shows a blank page, check internet access. `/openapi.json` works offline.

---

### Check 2: Offline transition alert rule

**Goal:** registering `RTR-101` returns 201; patching it to offline twice and then calling `GET /alerts` yields exactly **one** alert.

**Business rule:** an alert is created only when a stored device changes from `online` to `offline`. Registering a device as `offline` creates no alert, and repeating an `offline` update creates no extra alert.

> `RTR-101` must not already exist. If it does, the first step returns 409. Either [reset the data](#5-resetting-data) or use a new ID such as `RTR-102` in every command below.

#### Steps with curl

```bash
# 1. Register RTR-101 → expect 201 Created
curl -s -w "  [%{http_code}]\n" -X POST $B/devices -H "$J" \
  -d '{"device_id":"RTR-101","name":"Core router","device_type":"router","ip_address":"192.168.1.1"}'

# 2. Register it again → expect 409 Conflict
curl -s -w "  [%{http_code}]\n" -X POST $B/devices -H "$J" \
  -d '{"device_id":"RTR-101","name":"Core router","device_type":"router","ip_address":"192.168.1.1"}'

# 3. First offline PATCH → 200, status "offline", creates the alert
curl -s -w "  [%{http_code}]\n" -X PATCH $B/devices/RTR-101/status -H "$J" -d '{"status":"offline"}'

# 4. Second offline PATCH → 200, no new alert
curl -s -w "  [%{http_code}]\n" -X PATCH $B/devices/RTR-101/status -H "$J" -d '{"status":"offline"}'

# 5. Unknown device → expect 404 Not Found
curl -s -w "  [%{http_code}]\n" $B/devices/NOPE-1

# 6. List alerts → exactly one alert for RTR-101
curl -s -w "  [%{http_code}]\n" $B/alerts
```

Expected results:

| Step | Status | Body |
|---|---|---|
| 1 | 201 | `{"device_id":"RTR-101",...,"status":"online"}` |
| 2 | 409 | `{"detail":"Device already exists"}` |
| 3 | 200 | `{"device_id":"RTR-101",...,"status":"offline"}` |
| 4 | 200 | `{"device_id":"RTR-101",...,"status":"offline"}` |
| 5 | 404 | `{"detail":"Device not found"}` |
| 6 | 200 | `[{"device_id":"RTR-101","message":"Device RTR-101 went offline.","timestamp":"...Z"}]` |

Count the alerts for `RTR-101`:

```bash
curl -s $B/alerts | python -c 'import json,sys; print(sum(a["device_id"]=="RTR-101" for a in json.load(sys.stdin)))'
```

Expected output: `1`

#### Optional: no alert for initial offline registration

```bash
curl -s -X POST $B/devices -H "$J" \
  -d '{"device_id":"SW-201","name":"Lab switch","device_type":"switch","ip_address":"192.168.1.20","status":"offline"}'
curl -s -X PATCH $B/devices/SW-201/status -H "$J" -d '{"status":"offline"}'
curl -s $B/alerts | python -c 'import json,sys; print(sum(a["device_id"]=="SW-201" for a in json.load(sys.stdin)))'
```

Expected output: `0`

#### Same check in Swagger UI

1. **POST /devices** → **Try it out** → keep the `RTR-101` example → **Execute**. Expect **201**.
2. **PATCH /devices/{device_id}/status** → **Try it out** → `device_id` = `RTR-101`, body `{"status": "offline"}` → **Execute**. Expect **200**.
3. Click **Execute** again with the same values. Expect **200**.
4. **GET /alerts** → **Try it out** → **Execute**. Expect exactly one alert for `RTR-101`.

#### Input validation (optional)

| Request | Expected |
|---|---|
| `ip_address` of `"999.1.1.1"` or an IPv6 address | 422 (IPv4 only) |
| `device_type` of `"firewall"` | 422 (`router`, `switch`, `server` only) |
| `device_id` containing spaces or `/` | 422 (letters, digits, `-`, `_` only; maximum 50 characters) |
| `status` of `"down"` | 422 (`online` or `offline` only) |

---

### Check 3: Alembic and MySQL persistence

**Goal:** `alembic upgrade head` applies cleanly, the tables exist in MySQL, and data persists across restarts.

#### 3.1 Apply migrations and view history

```bash
alembic upgrade head
alembic current
alembic history --verbose
```

Expected results:

- `alembic current` prints `20261127_0002 (head)`.
- `alembic history` lists two revisions:
  - `20261127_0001`: create `devices` and `alerts` tables
  - `20261127_0002`: add optional `devices.location` column

#### 3.2 Confirm the tables exist in MySQL

```bash
sudo mysql netpulse_db -e "SHOW TABLES; DESCRIBE devices; DESCRIBE alerts;"
```

Expected tables: `alembic_version`, `alerts` and `devices`.

- `devices`: `device_id` VARCHAR(50) primary key, plus `name`, `device_type`, `ip_address`, `status`, `created_at`, `updated_at` and `location` (nullable).
- `alerts`: `id` auto-increment primary key, plus `device_id` (indexed foreign key to `devices.device_id`), `message` and `timestamp`.

#### 3.3 Verify the migrations are reversible (optional)

```bash
alembic downgrade -1    # back to 20261127_0001; drops devices.location
alembic current
alembic upgrade head    # back to 20261127_0002
alembic check           # expect: No new upgrade operations detected.
```

> `alembic downgrade -1` drops the `location` column and any values stored in it.

#### 3.4 Verify persistence across restarts

1. Complete [Check 2](#check-2-offline-transition-alert-rule) so that `RTR-101` and its alert exist.
2. Read the rows directly from MySQL:

   ```bash
   sudo mysql netpulse_db -e "SELECT device_id, name, status FROM devices; SELECT id, device_id, message, timestamp FROM alerts;"
   ```

3. Stop the API: press `Ctrl+C` in the uvicorn terminal, or run `pkill -f "uvicorn app.main:app"`.
4. Start it again:

   ```bash
   uvicorn app.main:app --reload
   ```

5. Query the API again:

   ```bash
   curl -s $B/devices/RTR-101
   curl -s $B/alerts
   ```

**Expected result:** `RTR-101` is still `offline`, and the same single alert is returned.

#### Creating future migrations

After changing a model in `app/db/models.py`:

```bash
alembic upgrade head                                      # database must be at head first
alembic revision --autogenerate -m "describe the change"  # review the generated file
alembic upgrade head
```

Do not regenerate the existing `location` migration; it is already in `alembic/versions/`.

---

### Check 4: Automated tests

**Goal:** `python -m pytest -q` passes across the service and persistence tests.

```bash
source .venv/bin/activate
python -m pytest -q
```

Expected output:

```text
................                                                         [100%]
16 passed in ...s
```

To list the tests that were skipped, along with the reasons:

```bash
python -m pytest -q -rs
```

#### What the tests cover

| File | Storage | Covers |
|---|---|---|
| `tests/test_device_service.py` | Fresh `InMemoryDeviceRepository` per test (fixture) | Registration, `DeviceAlreadyExistsError`, `DeviceNotFoundError`, no alert on offline registration, one alert on online-to-offline, no extra alert on repeated offline, a new alert after returning online and going offline again, device ID validation |
| `tests/test_mysql_device_repository.py` | Mocked SQLAlchemy session | Duplicate key (MySQL error 1062) → `DeviceAlreadyExistsError` with rollback, other integrity errors not mislabelled as duplicates, rollback on failed writes, detached domain objects returned, UTC alert timestamps, memory/MySQL backend selection |
| `tests/test_mysql_integration.py` | **Real MySQL** | `DeviceService` + `MySqlDeviceRepository`: duplicate IDs raise `DeviceAlreadyExistsError`; two offline PATCHes record exactly one alert; offline registration records none |
| `tests/test_db_session.py` | None | `get_db` closes sessions; ORM tables, primary key, foreign key and index compile for MySQL |

Notes:

- The MySQL integration tests run inside a transaction that is always rolled back, so they never change your data. You can confirm this by comparing row counts before and after a test run:

  ```bash
  sudo mysql netpulse_db -N -e "SELECT 'devices', COUNT(*) FROM devices UNION ALL SELECT 'alerts', COUNT(*) FROM alerts;"
  ```

- If MySQL is unreachable or the migrations have not been applied, the two integration tests are **skipped** rather than failed. The output then shows `14 passed, 2 skipped`.

---

### Check 5: Architecture explanation

NetPulse is a modular monolith. Each layer has a single responsibility:

```mermaid
flowchart LR
    Client[Client / Swagger UI] --> Routes
    Routes[Routes<br/>app/routes/] --> Service[DeviceService<br/>app/services/]
    Service --> Repo{{Repository interface}}
    Service --> Events[Events<br/>app/events.py]
    Events --> Repo
    Repo --> Mem[InMemoryDeviceRepository]
    Repo --> SQL[MySqlDeviceRepository]
    SQL --> DB[(MySQL)]
    Alembic[Alembic migrations<br/>alembic/] --> DB
```

| Layer | Location | Responsibility |
|---|---|---|
| **Routes** | `app/routes/devices.py`, `alerts.py`, `health.py`, `dependencies.py` | HTTP only. Validate input with Pydantic models (`app/models.py`), declare response models and status codes, translate `DeviceAlreadyExistsError` → 409 and `DeviceNotFoundError` → 404. `dependencies.py` selects the repository for each request: the shared in-memory instance, or a `MySqlDeviceRepository` bound to the request's database session from `get_db`. |
| **Service** | `app/services/device_service.py` | Business rules, independent of HTTP and SQL: reject duplicate IDs, raise not-found errors, and trigger an alert only on a stored online-to-offline transition. |
| **Repositories** | `app/repositories/device_repository.py`, `mysql_device_repository.py` | Storage behind one shared set of methods: `add_device`, `list_devices`, `get_device`, `update_status`, `save_alert`, `list_alerts`. The in-memory version keeps isolated per-instance state and returns copies. The MySQL version commits writes, rolls back on errors, maps duplicate keys to `DeviceAlreadyExistsError`, and returns Pydantic objects rather than ORM rows. |
| **Events** | `app/events.py` | `create_offline_alert(repository, device_id)` builds an alert with a clear message and a UTC timestamp, and records it only through `repository.save_alert()`. |
| **Database models and session** | `app/db/models.py`, `app/db/session.py`, `app/config.py` | SQLAlchemy ORM tables, kept separate from the API schemas; the engine, `SessionLocal` and the `get_db` dependency; and configuration read from `.env` and environment variables. |
| **Migrations** | `alembic/`, `alembic.ini` | Versioned schema changes. `env.py` reads the URL from `app/config.py` and compares against `Base.metadata`. Revision 0001 creates the tables; revision 0002 adds `location`. |

**Why this design matters:** because the service depends only on the repository's methods, switching storage from memory to MySQL changed no business rules. Only the repository injected per request changed, which is set by `NETPULSE_STORAGE`.

---

## 5. Resetting data

Use this to repeat Check 2 with `RTR-101`. **It deletes all devices and alerts.**

```bash
sudo mysql netpulse_db -e "DELETE FROM alerts; DELETE FROM devices;"
```

Alternatively, recreate the schema from scratch:

```bash
alembic downgrade base
alembic upgrade head
```

In memory mode (`NETPULSE_STORAGE=memory`), restarting uvicorn clears all data.

---

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Can't connect to MySQL server on 'localhost' ([Errno 111] Connection refused)` | MySQL is not running or not installed | `sudo systemctl enable --now mysql` (install it first if needed; see [Prerequisites](#1-prerequisites)) |
| `(1045, "Access denied for user ...")` | The MySQL user does not exist, or its password differs from `.env` | Repeat [2.3](#23-create-the-mysql-database-and-user) with the password from `.env`. Make sure `DATABASE_URL` matches the `MYSQL_*` values. |
| `(1049, "Unknown database ...")` | The database has not been created | Run `CREATE DATABASE netpulse_db ...` from [2.3](#23-create-the-mysql-database-and-user) |
| `Table 'netpulse_db.devices' doesn't exist` | Migrations have not been applied | `alembic upgrade head` |
| Data disappears after a restart | Storage mode is memory | Set `NETPULSE_STORAGE=mysql` in `.env`, then restart uvicorn |
| `POST /devices` returns 409 for `RTR-101` | The device already exists from an earlier run | Use a new ID, or [reset the data](#5-resetting-data) |
| `POST /devices` returns 422 | Invalid input (IP address, type, status, or ID format) | See [Input validation](#input-validation-optional) |
| `[Errno 98] address already in use` | An old server is still running on port 8000 | `pkill -f "uvicorn app.main:app"` |
| `/docs` page is blank | The Swagger UI CDN is unreachable | Check internet access; `/openapi.json` still works |
| `Command 'python' not found` | The virtual environment is not active | `source .venv/bin/activate` |
| 2 tests skipped | MySQL is unreachable or migrations are missing | Fix the MySQL connection, run `alembic upgrade head`, then `python -m pytest -q -rs` |

---

## 7. Command quick reference

```bash
# Environment
cd ~/NetPulse && source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl start mysql

# Migrations
alembic upgrade head
alembic current
alembic history --verbose
alembic downgrade -1 && alembic upgrade head
alembic check

# Database inspection
sudo mysql netpulse_db -e "SHOW TABLES; SELECT * FROM devices; SELECT * FROM alerts;"

# Run the API
uvicorn app.main:app --reload
pkill -f "uvicorn app.main:app"

# Tests
python -m pytest -q
python -m pytest -q -rs

# Scenario (second terminal)
B=http://127.0.0.1:8000; J='Content-Type: application/json'
curl -i -X POST $B/devices -H "$J" -d '{"device_id":"RTR-101","name":"Core router","device_type":"router","ip_address":"192.168.1.1"}'
curl -X PATCH $B/devices/RTR-101/status -H "$J" -d '{"status":"offline"}'
curl -X PATCH $B/devices/RTR-101/status -H "$J" -d '{"status":"offline"}'
curl $B/alerts
curl -i $B/devices/NOPE-1
```
