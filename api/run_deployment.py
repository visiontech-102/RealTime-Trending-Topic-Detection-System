import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

from db.connection import init_db_indexes, close_db_client
from jobs.deployment import run_deployed_pipeline, get_deployed_model


async def main():
    await init_db_indexes()
    winner = await get_deployed_model()
    if winner is None:
        print("ERROR: No winner set. Run 'python run_evaluation.py' first.")
        return
    print(f"Deployed model: {winner}")
    print("Running deployment pipeline...")
    result = await run_deployed_pipeline()
    print(f"Result: {result}")
    await close_db_client()


if __name__ == "__main__":
    asyncio.run(main())
