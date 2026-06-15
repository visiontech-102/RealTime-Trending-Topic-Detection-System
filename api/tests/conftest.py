"""Pytest configuration — run from api/: pytest tests/ -v"""
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio

API_ROOT = Path(__file__).resolve().parent.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

# Test database (isolated from production data)
os.environ.setdefault("DATABASE_NAME", "trending_topics_test")
os.environ.setdefault("MONGODB_URL", os.getenv("MONGODB_URL", "mongodb://localhost:27017/"))


def _mongo_available() -> bool:
    try:
        from pymongo import MongoClient
        client = MongoClient(os.environ["MONGODB_URL"], serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        client.close()
        return True
    except Exception:
        return False


mongo_integration = pytest.mark.skipif(
    not _mongo_available(),
    reason="MongoDB not available at MONGODB_URL",
)


@pytest_asyncio.fixture
async def test_db():
    """Provide a clean test database for integration tests."""
    from db.connection import reset_db_client, get_database, init_db_indexes, close_db_client

    reset_db_client(
        url=os.environ["MONGODB_URL"],
        name=os.environ["DATABASE_NAME"],
    )
    await init_db_indexes()
    db = await get_database()

    for coll in ("raw_tweets", "detected_trends", "pipeline_state", "topic_evolution", "users"):
        await db[coll].delete_many({})

    yield db

    for coll in ("raw_tweets", "detected_trends", "pipeline_state", "topic_evolution", "users"):
        await db[coll].delete_many({})
    await close_db_client()
    reset_db_client(
        url=os.getenv("MONGODB_URL", "mongodb://localhost:27017/"),
        name=os.getenv("DATABASE_NAME", "trending_topics_db"),
    )
