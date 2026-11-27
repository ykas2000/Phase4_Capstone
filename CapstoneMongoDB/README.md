# NetPulse

FastAPI modular monolith for registering network devices, tracking online/offline status, and raising an alert when a device goes from online to offline. Data is stored in MongoDB (or in memory for isolated runs).

Layout: `routes` (HTTP) → `services` (business rules) → `repositories` (in-memory or MongoDB); `events.py` creates offline alerts; `db/` holds the Mongo client, document helpers and indexes.

Full documentation with checkpoint screenshots: [docs/NetPulse_Project_Documentation.docx](docs/NetPulse_Project_Documentation.docx)

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # requires MongoDB on localhost:27017
uvicorn app.main:app --reload
```

Without MongoDB: `REPOSITORY_BACKEND=memory uvicorn app.main:app --reload`

API docs: http://127.0.0.1:8000/docs

## Test

```bash
python -m pytest -q
```

MongoDB tests are skipped automatically when MongoDB isn't reachable.
