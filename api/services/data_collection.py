import os
import logging
from datetime import datetime, timezone
import tweepy
from db.connection import get_database

logger = logging.getLogger(__name__)

class TweetCollector:
    """
    Handles collecting tweets from the Twitter API using Tweepy
    based on the strategy defined in the FYP Implementation Plan.
    """
    def __init__(self, bearer_token: str = None):
        self.bearer_token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN")
        self.client = None
        if self.bearer_token:
            self.client = tweepy.Client(bearer_token=self.bearer_token)
            logger.info("Tweepy Client initialized successfully.")
        else:
            logger.warning("No Twitter Bearer Token found in environment. Ingestion will rely on placeholder/manual entries.")

    async def ingest_tweet(
        self,
        tweet_id: str,
        text: str,
        lang: str,
        created_at: datetime,
        like_count: int = None,
        retweet_count: int = None,
    ) -> bool:
        """
        Ingests a raw tweet as unstructured text, preserving original content
        and temporal metadata, and saves it into the database.
        Returns True if newly inserted, False if skipped/error.
        """
        try:
            db = await get_database()
            raw_tweets_collection = db["raw_tweets"]
        except Exception as e:
            logger.error(f"Failed to access database for tweet ingestion: {e}")
            return False

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

        tweet_doc = {
            "id": tweet_id,
            "text": text,
            "lang_api": lang,
            "created_at": dt,
            "collected_at": datetime.now(timezone.utc),
            "retweet_count": retweet_count,
            "like_count": like_count,
        }

        try:
            # Prevent duplicate inserts using the unique index on 'id'
            await raw_tweets_collection.insert_one(tweet_doc)
            logger.info(f"Successfully ingested raw tweet: {tweet_id}")
            return True
        except Exception as e:
            # Check if this is a duplicate key error (code 11000)
            err_code = getattr(e, "code", None)
            if err_code == 11000 or "duplicate key" in str(e).lower():
                logger.debug(f"Tweet {tweet_id} already exists in database (duplicate skipped).")
            else:
                logger.error(f"Failed to insert tweet {tweet_id} due to database error: {e}", exc_info=True)
            return False

    def fetch_recent_tweets(self, query: str, max_results: int = 100):
        """
        Fetches recent tweets using the Tweepy Client based on defined query parameters
        """
        if not self.client:
            logger.warning("Tweepy Client is not initialized. Cannot fetch tweets.")
            return []

        try:
            response = self.client.search_recent_tweets(
                query=query,
                tweet_fields=['created_at', 'lang', 'public_metrics'],
                max_results=max_results
            )
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching tweets from Twitter API: {e}")
            return []

async def run_data_collection_pipeline(collector: TweetCollector, query_list: list, limit_per_query: int = 50) -> int:
    """
    Sequentially runs the data collection pipeline, queries Twitter API,
    and ingests raw tweets into the MongoDB database.
    Returns the count of successfully ingested new tweets.
    """
    logger.info("Starting Data Collection Pipeline...")
    ingested_count = 0
    for query in query_list:
        logger.info(f"Querying: '{query}'")
        tweets = collector.fetch_recent_tweets(query, max_results=limit_per_query)
        for tweet in tweets:
            metrics = getattr(tweet, "public_metrics", None) or {}
            success = await collector.ingest_tweet(
                tweet_id=str(tweet.id),
                text=tweet.text,
                lang=tweet.lang or "und",
                created_at=tweet.created_at,
                like_count=metrics.get("like_count"),
                retweet_count=metrics.get("retweet_count"),
            )
            if success:
                ingested_count += 1
    logger.info("Data Collection Ingestion Cycle Completed.")
    return ingested_count
