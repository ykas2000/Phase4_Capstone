from threading import Lock

from pymongo import MongoClient
from pymongo.database import Database

from app.config import get_settings

_client: MongoClient | None = None
_lock = Lock()


def get_client() -> MongoClient:
    """Return the shared MongoClient, creating it on first use."""
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                # MongoClient connects lazily, so this does not require a running server.
                _client = MongoClient(
                    get_settings().mongodb_uri,
                    serverSelectionTimeoutMS=5000,
                    tz_aware=True,
                )
    return _client


def get_database() -> Database:
    return get_client()[get_settings().mongodb_db_name]


get_db = get_database


def close_client() -> None:
    global _client
    with _lock:
        if _client is not None:
            _client.close()
            _client = None
