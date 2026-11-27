import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str
    mongodb_db_name: str
    devices_collection: str
    alerts_collection: str
    repository_backend: str


@lru_cache
def get_settings() -> Settings:
    # Real environment variables take precedence over values in .env.
    load_dotenv()
    return Settings(
        mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
        mongodb_db_name=os.getenv("MONGODB_DB_NAME", "netpulse_db"),
        devices_collection=os.getenv("DEVICES_COLLECTION", "devices"),
        alerts_collection=os.getenv("ALERTS_COLLECTION", "alerts"),
        repository_backend=os.getenv("REPOSITORY_BACKEND", "mongo").strip().lower(),
    )
