from uuid import uuid4

import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.config import get_settings
from app.db.collections import ensure_indexes


@pytest.fixture(scope="session")
def mongo_client():
    client = MongoClient(get_settings().mongodb_uri, serverSelectionTimeoutMS=1000, tz_aware=True)
    try:
        client.admin.command("ping")
    except PyMongoError:
        client.close()
        pytest.skip("MongoDB not reachable at MONGODB_URI")
    yield client
    client.close()


@pytest.fixture
def mongo_db(mongo_client):
    # Throwaway database per test so tests never touch real data or each other.
    name = f"netpulse_test_{uuid4().hex[:12]}"
    db = mongo_client[name]
    ensure_indexes(db)
    yield db
    mongo_client.drop_database(name)
