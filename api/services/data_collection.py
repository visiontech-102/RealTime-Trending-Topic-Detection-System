import os
import logging
from datetime import datetime, timezone
import tweepy
from pymongo.errors import DuplicateKeyError
import asyncio
from db.connection import get_database

logger = logging.getLogger(__name__)

class TweetCollector:
    
    """Handles collecting tweets from the Twitter API using Tweepy."""

    def __init__(self, bearer_token: str = None):
        self.bearer_token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN")
        self.client = None
        if self.bearer_token:
            self.client = tweepy.Client(bearer_token=self.bearer_token)
            logger.info("Tweepy Client initialized successfully.")
        else:
            logger.warning("No Twitter Bearer Token found in environment. Ingestion will rely on placeholder/manual entries.")

    async def ingest_tweet(self, tweet_id: str, text: str, lang: str, created_at: datetime, metrics: dict = None) -> bool:
        """
        Ingests a raw tweet as unstructured text, preserving original content
        and temporal metadata, and saves it into the database.
        """
        db = await get_database()
        raw_tweets_collection = db["raw_tweets"]


        # Ensure timezone-aware UTC datetime
        if isinstance(created_at, str):
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                dt = datetime.now(timezone.utc)
        elif created_at.tzinfo is None:
            dt = created_at.replace(tzinfo=timezone.utc)
        else:
            dt = created_at
        metrics = metrics or {}
        tweet_doc = {
            "id": tweet_id,
            "text": text,
            "lang_api": lang,
            "created_at": dt,
            "collected_at": datetime.now(timezone.utc),
            "retweet_count": metrics.get("retweet_count", 0),
            "like_count": metrics.get("like_count", 0),
        }

        try:
            await raw_tweets_collection.insert_one(tweet_doc)
            logger.info(f"Successfully ingested raw tweet: {tweet_id}")
            return True
        except DuplicateKeyError:
            logger.debug(f"Duplicate skipped: {tweet_id}")
            return False
        except Exception as e:
            logger.error(f"REAL ERROR for tweet {tweet_id}: {e}")
            raise

    async def fetch_recent_tweets(self, query: str, max_results: int = 10):
        """
        Fetches recent tweets using the Tweepy Client based on defined query parameters
        """
        max_results = max(10, min(max_results, 100))

        if not self.client:
            logger.warning("Tweepy Client is not initialized. Cannot fetch tweets.")
            return []

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.search_recent_tweets(
                    query=query,
                    tweet_fields=["created_at", "lang", "public_metrics"],
                    max_results=max_results,
                )
            )
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching tweets from Twitter API: {e}")
            return []

async def run_data_collection_pipeline(collector: TweetCollector, query_list: list, limit_per_query: int = 50):
    """
    Sequentially runs the data collection pipeline, queries Twitter API,
    and ingests raw tweets into the MongoDB database.
    """
    logger.info("Starting Data Collection Pipeline...")
    ingested = 0
    for query in query_list:
        logger.info(f"Querying: '{query}'")
        tweets = await collector.fetch_recent_tweets(query, max_results=limit_per_query)
        for tweet in tweets:
            # Preserving raw unstructured text, language code, and temporal metadata
            saved = await collector.ingest_tweet(
                tweet_id=str(tweet.id),
                text=tweet.text,
                lang=tweet.lang,
                created_at=tweet.created_at,
                metrics=tweet.public_metrics,
            )
            if saved:
                ingested += 1
    logger.info("Data Collection Ingestion Cycle Completed.")
    return ingested
