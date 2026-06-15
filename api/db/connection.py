import os
import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
DATABASE_NAME = os.getenv("DATABASE_NAME", "trending_topics_db")

_client: Optional[AsyncIOMotorClient] = None
_db = None
_verified = False  # Track whether connection has been validated


def _ensure_client():
    global _client, _db
    if _client is None:
        _client = AsyncIOMotorClient(MONGODB_URL)
        _db = _client[DATABASE_NAME]
    return _client, _db


async def get_database():
    global _verified
    _, database = _ensure_client()
    if not _verified:
        try:
            # Verify database connection by sending a ping command
            await database.command("ping")
            _verified = True
            logger.info("Successfully connected to MongoDB database '%s' at %s", DATABASE_NAME, MONGODB_URL)
        except Exception as e:
            logger.error("Failed to connect to MongoDB database '%s' at %s: %s", DATABASE_NAME, MONGODB_URL, e)
            _verified = False
            raise ConnectionError(f"Database connection verification failed: {e}") from e
    return database


async def init_db_indexes():
    """Creates necessary indexes to ensure data integrity and prevent duplicates."""
    _, database = _ensure_client()
    try:
        await database["raw_tweets"].create_index("id", unique=True)
        await database["raw_tweets"].create_index("collected_at")
        await database["detected_trends"].create_index("calculated_at")
        await database["detected_trends"].create_index("lang")
        await database["topic_evolution"].create_index("stored_at")
        await database["pipeline_state"].create_index("pipeline", unique=True)
        logger.info("Database indexes initialized successfully.")
    except Exception as e:
        logger.error("Error initializing database indexes: %s", e)


async def deduplicate_existing_trends():
    """Identifies and removes duplicate records from the detected_trends collection,
    keeping only the latest document (based on calculated_at) for each unique Name,
    and assigns a unique sequential topic number to each document."""
    from datetime import datetime
    db = await get_database()
    coll = db["detected_trends"]
    
    # 1. Group duplicates by Name
    pipeline = [
        {
            "$group": {
                "_id": "$Name",
                "count": {"$sum": 1},
                "docs": {
                    "$push": {
                        "id": "$_id",
                        "calculated_at": "$calculated_at"
                    }
                }
            }
        },
        {
            "$match": {
                "count": {"$gt": 1}
            }
        }
    ]
    
    cursor = coll.aggregate(pipeline)
    deleted_count = 0
    async for group in cursor:
        docs = group["docs"]
        # Sort documents by calculated_at descending to keep the latest one
        docs.sort(key=lambda d: d.get("calculated_at") or datetime.min, reverse=True)
        
        # Keep the first one (latest), delete the rest
        to_delete_ids = [d["id"] for d in docs[1:]]
        if to_delete_ids:
            res = await coll.delete_many({"_id": {"$in": to_delete_ids}})
            deleted_count += res.deleted_count
            
    # 2. Assign unique sequential topic numbers (0, 1, 2...) and update Name prefix
    import re
    cursor_all = coll.find({}).sort("calculated_at", 1)
    all_docs = await cursor_all.to_list(length=1000)
    for idx, doc in enumerate(all_docs):
        old_name = doc.get("Name", "")
        clean_name_part = re.sub(r'^-?\d+_', '', old_name)
        new_name = f"{idx}_{clean_name_part}"
        await coll.update_one(
            {"_id": doc["_id"]},
            {"$set": {"topic": idx, "Name": new_name}}
        )
            
    if deleted_count > 0:
        logger.info("Deduplication complete: removed %d duplicate trend documents. Assigned unique sequential topic numbers to %d trends.", deleted_count, len(all_docs))
    else:
        logger.info("Deduplication complete: no duplicate trends found. Assigned unique sequential topic numbers to %d trends.", len(all_docs))
    return deleted_count



async def close_db_client():
    """Close Motor client on application shutdown."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB client closed.")


def reset_db_client(url: Optional[str] = None, name: Optional[str] = None):
    """Reset client (for integration tests). Call before any DB access in tests."""
    global _client, _db, MONGODB_URL, DATABASE_NAME, _verified
    if url is not None:
        MONGODB_URL = url
    if name is not None:
        DATABASE_NAME = name
    if _client is not None:
        _client.close()
    _client = None
    _db = None
    _verified = False  # Reset verification on client reset
