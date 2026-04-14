import os
import asyncio
import json
import random
from datetime import datetime
from urllib.parse import unquote
import tweepy
from database.connection import get_database


def get_twitter_bearer_token():
    raw_token = os.getenv("TWITTER_BEARER_TOKEN", "")
    decoded_token = unquote(raw_token).strip()

    if decoded_token:
        print(
            f"DEBUG: TWITTER_BEARER_TOKEN loaded, length={len(decoded_token)}, "
            f"url_encoded={'%' in raw_token}, first10={decoded_token[:10]}..., last4={decoded_token[-4:]}"
        )
    else:
        print("DEBUG: TWITTER_BEARER_TOKEN is empty after loading environment.")

    return decoded_token

MOCK_SOMALI_TWEETS = [
    "Qarax xoogan ayaa maanta ka dhacay magaalada Muqdisho. #Soomaaliya",
    "Doorashada madaxweynaha ayaa la filayaa in ay qabsoonto bisha soo socta.",
    "Banaanbax nabadeed ayaa ka dhacay bartamaha magaalada Hargeysa.",
    "Abaarta ka jirta gobolada qaar ayaa laga deyrinayaa.",
    "Ganacsiga Soomaaliya ayaa horumar la taaban karo sameynaya sanadihii dambe."
]

MOCK_ENGLISH_TWEETS = [
    "AI is transforming the way we build software in 2026. #AI #Tech",
    "The stock market saw a massive increase today following the tech earnings report.",
    "Climate change discussions dominate the global summit.",
    "A new deep learning model has been open-sourced.",
    "SpaceX successfully launched another mission to Mars."
]

# Simple background task for mockup streaming if keys are not provided
async def mock_twitter_stream():
    db = await get_database()
    tweets_collection = db["raw_tweets"]
    
    print("Loading cleaned historical data from database to simulate stream...")
    # Fetch existing true tweets for English
    cursor_en = tweets_collection.find({"language": "en"}).sort("timestamp", -1).limit(100)
    en_tweets = [doc["text"] for doc in await cursor_en.to_list(length=100)]
    
    # Fetch existing true tweets for Somali
    cursor_so = tweets_collection.find({"language": "so"}).sort("timestamp", -1).limit(100)
    so_tweets = [doc["text"] for doc in await cursor_so.to_list(length=100)]
    
    en_pool = en_tweets if en_tweets else MOCK_ENGLISH_TWEETS
    so_pool = so_tweets if so_tweets else MOCK_SOMALI_TWEETS
    
    while True:
        # Randomly choose language
        lang = random.choice(["en", "so"])
        text = random.choice(en_pool) if lang == "en" else random.choice(so_pool)
        
        tweet_doc = {
            "tweet_id": str(random.randint(1000000, 9999999)),
            "text": text,
            "language": lang,
            "timestamp": datetime.utcnow(),
            "engagement_metrics": random.randint(0, 1000)
        }
        
        await tweets_collection.insert_one(tweet_doc)
        print(f"DB-Mock INGEST: [{lang}] {text[:60]}...")
        
        # Sleep random time between 5-15 seconds
        await asyncio.sleep(random.randint(5, 15))


class CustomStream(tweepy.StreamingClient):
    def __init__(self, bearer_token, max_tweets=100, loop=None, **kwargs):
        super().__init__(bearer_token, **kwargs)
        self.tweet_count = 0
        self.max_tweets = max_tweets
        self.loop = loop

    def on_tweet(self, tweet):
        self.tweet_count += 1
        # Schedule async insert in the main event loop
        if self.loop:
            self.loop.create_task(self.insert_tweet(tweet))
        else:
            # Fallback if no loop
            asyncio.create_task(self.insert_tweet(tweet))
        
        if self.tweet_count >= self.max_tweets:
            print(f"\n[LIMIT REACHED] Reached maximum of {self.max_tweets} tweets. Disconnecting stream...")
            self.disconnect()

    async def insert_tweet(self, tweet):
        db = await get_database()
        tweets_collection = db["raw_tweets"]
        
        lang = "so" if "so" in tweet.text.lower() else "en" # Very basic lang detection
        tweet_doc = {
            "tweet_id": str(tweet.id),
            "text": tweet.text,
            "language": tweet.lang or lang,
            "timestamp": tweet.created_at or datetime.utcnow(),
            "engagement_metrics": 0
        }
        
        await tweets_collection.insert_one(tweet_doc)
        print(f"Tweepy INGEST: {tweet.text}")

    def on_error(self, status):
        print(f"Error on stream: {status}")


async def start_stream():
    """Start either a Tweepy stream or a mock stream based on loaded ENV keys."""
    bearer_token = get_twitter_bearer_token()
    max_tweets = int(os.getenv("MAX_TWEETS_PER_RUN", "1000"))

    if bearer_token:
        print(f"Starting real Twitter Stream via Tweepy... (Limit: {max_tweets} tweets per run)")
        loop = asyncio.get_running_loop()
        stream = CustomStream(bearer_token, max_tweets=max_tweets, loop=loop)

        try:
            client = tweepy.Client(bearer_token=bearer_token)
            try:
                client.get_user(username="twitterdev")
                print("DEBUG: Bearer token validation succeeded.")
            except Exception as auth_error:
                print(f"DEBUG: Bearer token validation failed: {type(auth_error).__name__}: {auth_error}")
                raise auth_error

            stream.add_rules(tweepy.StreamRule("has:hashtags lang:en OR has:hashtags lang:so"))
            stream.filter(threaded=True)
        except Exception as e:
            print(f"Error starting tweepy stream ({type(e).__name__}): {repr(e)}. Falling back to mock stream.")
            await mock_twitter_stream()
    else:
        print("No Twitter Bearer Token found. Starting MOCK Twitter Stream...")
        await mock_twitter_stream()
