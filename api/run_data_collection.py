import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Add the api directory to path so imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import init_db_indexes, get_database, close_db_client
from services.data_collection import TweetCollector, run_data_collection_pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def main():
    load_dotenv()
    
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        print("WARNING: TWITTER_BEARER_TOKEN is not set in your .env file.")
        print("Data collection will run, but it won't be able to fetch live tweets from Twitter/X API.")
        print("Please ensure TWITTER_BEARER_TOKEN is configured in api/.env.")
        print("-" * 50)
    
    print("Connecting to MongoDB and initializing indexes...")
    try:
        await init_db_indexes()
        db = await get_database()
        print("Successfully connected to MongoDB!")
    except Exception as e:
        print(f"CRITICAL ERROR: Could not connect to MongoDB: {e}")
        return

    collector = TweetCollector(bearer_token=bearer_token)
    
    # Standard query list from app/main.py
    queries = [
        "(dowladda OR xukuumada OR doorasho OR baarlamaanka OR madaxweyne OR raysalwasaare OR wasiir OR siyaasad OR golaha OR dastuurka OR xildhibaan) -is:retweet -is:reply",
        "(amniga OR dagaal OR weerar OR ciidamada OR alshabaab OR qarax OR nabadgelyo OR howlgal OR argagixiso OR difaaca) -is:retweet -is:reply",
        "(dhaqaalaha OR ganacsiga OR lacagta OR suuqa OR shacabka OR gargaar OR abaaraha OR barakac OR caafimaad OR waxbarasho OR kubadda) -is:retweet -is:reply",
        "(#Soomaaliya OR #Somalia OR #SomaliTwitter OR #Muqdisho OR #Mogadishu OR #Somaliland OR #Puntland OR #Galmudug OR #Hirshabelle OR #Koofurgalbeed OR #Jubaland OR #Banadir OR #Villasomalia) -is:retweet -is:reply",
    ]
    
    print(f"Starting data collection for {len(queries)} queries...")
    try:
        ingested = await run_data_collection_pipeline(collector, queries, limit_per_query=50)
        print(f"Success! Newly ingested tweets: {ingested}")
    except Exception as e:
        print(f"Error running data collection pipeline: {e}")
    finally:
        await close_db_client()
        print("Database connection closed.")

if __name__ == "__main__":
    asyncio.run(main())
