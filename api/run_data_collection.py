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
        "(crime OR investigation OR lawsuit OR corruption OR fraud OR trial OR verdict OR police OR prison OR indictment OR scandal OR arrest OR homicide OR courtroom OR justice) lang:en -is:retweet -is:reply",
        "(education OR university OR tuition OR scholarship OR studentloan OR curriculum OR literacy OR classroom OR teacher OR enrollment OR graduation OR STEM OR onlinelearning OR admissions) lang:en -is:retweet -is:reply",
        "(entertainment OR celebrity OR boxoffice OR streaming OR grammy OR oscars OR concert OR album OR premiere OR bollywood OR hollywood OR gaming OR esports OR viral) lang:en -is:retweet -is:reply",
        "(#Hollywood OR #Grammys OR #Oscars OR #Gaming OR #Esports OR #Education OR #CrimeNews OR #Justice OR #Streaming OR #PopCulture OR #TrueCrime OR #Celebrity OR #BoxOffice) lang:en -is:retweet -is:reply",
    ]

    # queries = [
    #     "(dowladda OR xukuumada OR doorasho OR baarlamaanka OR madaxweyne OR raysalwasaare OR wasiir OR siyaasad OR golaha OR dastuurka OR xildhibaan OR maamulka OR doorashada) -is:retweet -is:reply",
    #     "(amniga OR dagaal OR weerar OR ciidamada OR alshabaab OR qarax OR nabadgelyo OR howlgal OR argagixiso OR difaaca OR khawaarij OR hubaysan) -is:retweet -is:reply",
    #     "(dhaqaalaha OR ganacsiga OR lacagta OR suuqa OR shacabka OR gargaar OR abaaraha OR barakac OR caafimaad OR waxbarasho OR kubadda OR roobabka OR fatahaad) -is:retweet -is:reply",
    #     "(#Soomaaliya OR #Somalia OR #SomaliTwitter OR #Muqdisho OR #Mogadishu OR #Somaliland OR #Puntland OR #Galmudug OR #Hirshabelle OR #Koofurgalbeed OR #Jubaland OR #Banadir OR #Villasomalia) -is:retweet -is:reply",
    # ]

    # queries = [
    #     "(safarka OR dalxiisaha OR duulimaadyada OR hotelada OR xeebaha OR beeraha-dalxiiska OR magaalooyinka OR bandhigyada OR ciyaaraha-dibedda OR socdaalka) -is:retweet -is:reply",
    #     "(riyaaqada OR fashinka OR cuntada OR maqaayadaha OR sanka-iyo-quruxda OR dharka OR filimada OR telefishinka OR musalsalada OR baraha-bulshada-madadaalada) -is:retweet -is:reply",
    #     "(kubadda-cagta OR kubadda-koleyga OR ciyaaraha OL-ka OR tartannada-caalamiga OR kooxaha-soomaaliyeed OR ciyaartoyda OR koobabka-caalamiga OR gymnastics OR isboortiga-dumarka OR tababarayaasha) -is:retweet -is:reply",
    #     "(#DalxiiskaSoomaaliya OR #MadadaaladaSoomaaliyeed OR #IsboortigaSoomaaliya OR #KubaddaCagtaSoomaaliyeed OR #FilimadaSoomaaliyeed OR #FashinkaSoomaaliyeed OR #CuntadaSoomaaliyeed OR #DalxiisSoomaaliyeed OR #CiyaaraheenSoomaaliyeed) -is:retweet -is:reply",
    # ]

    print(f"Starting data collection for {len(queries)} queries...")
    try:
        ingested = await run_data_collection_pipeline(collector, queries, limit_per_query=1000)
        print(f"Success! Newly ingested tweets: {ingested}")
    except Exception as e:
        print(f"Error running data collection pipeline: {e}")
    finally:
        await close_db_client()
        print("Database connection closed.")

if __name__ == "__main__":
    asyncio.run(main())
