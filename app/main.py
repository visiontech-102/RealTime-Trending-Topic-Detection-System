from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from dotenv import load_dotenv

load_dotenv()

from app.routes import router
from services.twitter_stream import start_stream
from services.ai_engine import run_ai_loop

app = FastAPI(title="Real-Time Trending Topic Detection API", version="1.0.0")

# CORS config allowing frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Since this is local testing, allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.on_event("startup")
async def startup_event():
    print("Starting background workers...")
    # Start the Twitter Data Ingestion stream
    asyncio.create_task(start_stream())
    # Start the BERTopic clustering engine loop
    asyncio.create_task(run_ai_loop())

@app.get("/")
def read_root():
    return {"message": "Welcome to the Vision Tech Trending Topics API"}
