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

            if ingested > 0:
                try:
                    from jobs.deployment import get_deployed_model, run_deployed_pipeline
                    deployed = await get_deployed_model()
                    if deployed:
                        threshold = int(os.getenv("BERTOPIC_NEW_TWEETS_THRESHOLD", "1000"))
                        db_inst = await get_database()
                        state = await db_inst["pipeline_state"].find_one({"pipeline": deployed})
                        last_ts = state.get("last_trained_tweet_collected_at") if state else None
                        if last_ts:
                            new_count = await db_inst["raw_tweets"].count_documents({"collected_at": {"$gt": last_ts}})
                            if new_count >= threshold:
                                deploy_result = await run_deployed_pipeline()
                                print(f"Post-collection deployment: {deploy_result}")
                            else:
                                print(f"Post-collection: {new_count}/{threshold} new tweets — deployment skipped")
                        else:
                            deploy_result = await run_deployed_pipeline()
                            print(f"Post-collection deployment (first run): {deploy_result}")
                except Exception as de:
                    print(f"Post-collection deployment error (non-fatal): {de}")
        except Exception as e:
            print(f"Error in background data collection loop: {e}")
        await asyncio.sleep(15 * 60)



async def periodic_model_comparison_loop():
    """
    One-time evaluation loop: runs the three-way evaluation ONCE to select the
    initial winner, then exits permanently.

    Once a winner is set it is never changed automatically — re-evaluation is
    a manual academic decision (POST /jobs/run-evaluation?force=true).
    If the corpus is too small the loop retries every 30 minutes until enough
    data has been collected, then runs evaluation and exits.
    """
    retry_minutes = int(os.getenv("BERTOPIC_TRAIN_INTERVAL_MINUTES", "30"))
    await asyncio.sleep(300)  # 5-min startup delay

    while True:
        try:
            from jobs.deployment import get_deployed_model, run_deployed_pipeline
            deployed = await get_deployed_model()
            if deployed is not None:
                # Winner already determined — this loop's job is done.
                print(f"INFO: Evaluation loop: winner '{deployed}' already set. Exiting — manual re-evaluation only.")
                return

            from jobs.evaluation_pipeline import run_full_evaluation
            result = await run_full_evaluation()
            status = result.get("status")
            winner = result.get("deployed_model")
            print(f"Initial evaluation: status={status}, winner={winner}")

            if status == "success" and winner:
                # Immediately write winner's topics so the frontend is not empty.
                try:
                    deploy_result = await run_deployed_pipeline()
                    print(f"Post-evaluation deployment: {deploy_result}")
                except Exception as de:
                    print(f"Post-evaluation deployment error (non-fatal): {de}")
                return  # Winner found — loop exits permanently.

            # Not enough data yet — retry after interval.
            await asyncio.sleep(retry_minutes * 60)
        except Exception as e:
            print(f"Error in evaluation loop: {e}")
            await asyncio.sleep(retry_minutes * 60)


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
