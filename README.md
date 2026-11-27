# NetPulse

Minimal FastAPI device API. Device data is stored in memory and resets when the process restarts.

See [docs/RUNBOOK.md](docs/RUNBOOK.md) for full setup, scenario checks, and troubleshooting.

Install dependencies and start the development server from the project root:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive documentation is at `/docs`.

To use MySQL storage, copy `.env.example` to `.env`, set the connection values and `NETPULSE_STORAGE=mysql`, then run `alembic upgrade head` before starting the API. `DATABASE_URL`, when set, overrides the individual MySQL settings. The default `NETPULSE_STORAGE=memory` keeps data in memory.

## Migrations

The checked-in second migration adds a nullable `devices.location` column. With a configured MySQL database, apply it and inspect the migration history with:

```bash
alembic upgrade head
alembic current
alembic history --verbose
```

To demonstrate rolling back and reapplying the latest revision:

```bash
alembic downgrade -1
alembic upgrade head
```

Downgrading the location migration removes the column and any values stored in it.

For a future schema change, first upgrade the database to the current head, change the ORM model, then generate and review a new migration before applying it:

```bash
alembic revision --autogenerate -m "describe schema change"
alembic upgrade head
```

Autogeneration requires a live connection to the configured MySQL database. The location migration is already included; do not generate it again.