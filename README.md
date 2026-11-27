# NetPulse

Minimal FastAPI device API. Device data is stored in memory and resets when the process restarts.


<img width="2879" height="1722" alt="Screenshot 2026-11-27 095612" src="https://github.com/user-attachments/assets/34c83780-436a-477e-9c1f-42b73a45ac75" />


<img width="2879" height="1715" alt="Screenshot 2026-11-27 095627" src="https://github.com/user-attachments/assets/b9a3a1c5-b0d4-44ca-949f-feb0b15ff564" />


See [docs/RUNBOOK.md](docs/RUNBOOK.md) for full setup, scenario checks, and troubleshooting.

See [docs/PROJECT_GUIDE.md](docs/PROJECT_GUIDE.md) for the project description and a step-by-step walkthrough with execution screenshots.





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
