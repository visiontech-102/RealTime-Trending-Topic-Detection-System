"""
Standalone entry point: trains LDA, NMF, and BERTopic on the real raw_tweets
corpus and writes the three-way intrinsic evaluation to results/.

Usage (from api/):
    python run_evaluation.py
"""
import asyncio
import logging

from jobs.evaluation_pipeline import run_full_evaluation

logging.basicConfig(level=logging.INFO)


async def main():
    result = await run_full_evaluation()
    print(f"\nStatus: {result['status']}")


if __name__ == "__main__":
    asyncio.run(main())
