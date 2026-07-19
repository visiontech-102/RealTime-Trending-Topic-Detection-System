import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

from db.connection import init_db_indexes, close_db_client
from jobs.bertopic_pipeline import run_bertopic_pipeline


async def main():
    await init_db_indexes()
    print("Running BERTopic pipeline...")
    result = await run_bertopic_pipeline()
    print(f"Result: {result}")
    await close_db_client()


if __name__ == "__main__":
    asyncio.run(main())
