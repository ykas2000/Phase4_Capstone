# NetPulse

Minimal FastAPI device API. Device data is stored in memory and resets when the process restarts.

Install dependencies and start the development server from the project root:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive documentation is at `/docs`.