import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.routes import router
from db.connection import init_db_indexes, get_database, close_db_client, deduplicate_existing_trends
from services.data_collection import TweetCollector, run_data_collection_pipeline
from jobs.bertopic_pipeline import run_bertopic_pipeline
from jobs.model_comparison import run_model_comparison
from services.notifications import send_daily_digests

BACKGROUND_TASKS: list[asyncio.Task] = []


async def periodic_data_collection_loop(app: FastAPI):
    """Background worker that runs the data collection pipeline periodically."""
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        print("WARNING: TWITTER_BEARER_TOKEN is not set. Background data collection is disabled.")
        return

    collector = TweetCollector(bearer_token=bearer_token)
    queries = [  
             # 1 — Siyaasad & dowlad
             "(dowladda OR xukuumada OR doorasho OR baarlamaanka OR madaxweyne OR raysalwasaare OR wasiir OR siyaasad OR musharraxa OR xisbiga OR golaha OR dastuurka OR xildhibaan ) -is:retweet -is:reply",
             # 2 — Amni & dagaal
             "(amniga OR dagaal OR weerar OR warar OR wareysi OR ciidamada OR alshabaab OR qarax OR nabadgelyo OR howlgal OR argagixiso OR difaaca OR magaalada OR burbur) -is:retweet -is:reply",
             # 3 — Dhaqaale, bulsho & gargaar
             "(dhaqaalaha OR ganacsiga OR lacagta OR suuqa OR shacabka OR gargaar OR abaaraha OR barakac OR caafimaad OR waxbarasho OR kubadda OR ciyaaraha OR koobka OR adduunka OR bulsho OR heshiis OR qabiil OR  ) -is:retweet -is:reply",
             # 4 — Hashtag & gobollo
             "(#Soomaaliya OR #Somalia OR #SomaliTwitter OR #Muqdisho OR #Mogadishu OR #Somaliland OR #Puntland OR #Galmudug OR #Hirshabelle OR #Koofurgalbeed OR #Jubaland OR #Banadir OR #Villasomalia) -is:retweet -is:reply",
    ]

    while True:
        try:
            # 1. Check if the session quota limit has been reached
            if app.state.session_ingested_count >= app.state.max_quota_limit:
                print(f"INFO: Quota shield is active. Ingested {app.state.session_ingested_count}/{app.state.max_quota_limit} tweets in this session. Ingestion loop strictly STOPPED.")
                break  # STRICT STOP: The loop stops completely!

            # 2. Dynamic limit: only fetch remaining tweets to not exceed the limit
            remaining = app.state.max_quota_limit - app.state.session_ingested_count
            limit_per_query = max(1, min(50, remaining // len(queries)))

            print(f"INFO: Ingestion starting. Current session count={app.state.session_ingested_count}/{app.state.max_quota_limit}. Fetching up to {limit_per_query} tweets per query.")

            ingested = await run_data_collection_pipeline(collector, queries, limit_per_query=limit_per_query)
            app.state.session_ingested_count += ingested

            print(f"INFO: Ingestion cycle complete. Newly ingested: {ingested}. Session total count: {app.state.session_ingested_count}/{app.state.max_quota_limit}")
        except Exception as e:
            print(f"Error in background data collection loop: {e}")
        await asyncio.sleep(15 * 60)


async def periodic_bertopic_training_loop():
    """Trains BERTopic on ingested corpus and writes detected_trends."""
    interval_minutes = int(os.getenv("BERTOPIC_TRAIN_INTERVAL_MINUTES", "30"))
    await asyncio.sleep(120)

    while True:
        try:
            result = await run_bertopic_pipeline()
            print(f"BERTopic training cycle: {result}")
        except Exception as e:
            print(f"Error in BERTopic training loop: {e}")
        await asyncio.sleep(interval_minutes * 60)


async def periodic_model_comparison_loop():
    """Refresh comparison report after both pipelines have run."""
    interval_hours = int(os.getenv("COMPARISON_INTERVAL_HOURS", "168"))
    await asyncio.sleep(600)

    while True:
        try:
            db = await get_database()
            lda = await db["pipeline_state"].find_one({"pipeline": "lda"})
            bertopic = await db["pipeline_state"].find_one({"pipeline": "bertopic"})
            if lda and bertopic:
                result = await run_model_comparison()
                print(f"Model comparison cycle: {result.get('status')}")
        except Exception as e:
            print(f"Error in model comparison loop: {e}")
        await asyncio.sleep(interval_hours * 3600)


async def periodic_email_digest_loop():
    """Send daily digests to users with email_digests enabled."""
    interval_hours = int(os.getenv("DIGEST_INTERVAL_HOURS", "24"))
    await asyncio.sleep(300)

    while True:
        try:
            result = await send_daily_digests()
            print(f"Email digest cycle: {result}")
        except Exception as e:
            print(f"Error in email digest loop: {e}")
        await asyncio.sleep(interval_hours * 3600)


def _start_background_task(coro):
    task = asyncio.create_task(coro)
    BACKGROUND_TASKS.append(task)
    return task


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: DB indexes + background workers. Shutdown: cancel tasks, close MongoDB."""
    print("Initializing Database Indexes...")
    db_connected = False
    try:
        await init_db_indexes()
        print("Deduplicating existing trends in database...")
        await deduplicate_existing_trends()
        db = await get_database()
        await db.command("ping")
        db_connected = True
        print("Database connection verified successfully.")
    except Exception as e:
        print("Database not connected")
        print(f"CRITICAL ERROR Details: {e}")

    if db_connected:
        app.state.data_collection_task = _start_background_task(periodic_data_collection_loop(app))
        _start_background_task(periodic_bertopic_training_loop())
        _start_background_task(periodic_model_comparison_loop())
        _start_background_task(periodic_email_digest_loop())

    yield

    print("Shutting down background tasks...")
    for task in BACKGROUND_TASKS:
        task.cancel()
    await asyncio.gather(*BACKGROUND_TASKS, return_exceptions=True)
    BACKGROUND_TASKS.clear()
    await close_db_client()
    print("Shutdown complete.")


app = FastAPI(
    title="Real-Time Trending Topic Detection API",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.session_ingested_count = 0
app.state.max_quota_limit = 1000

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Vision Tech Trending Topics API"}
