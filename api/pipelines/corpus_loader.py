"""
Loads tweet corpora from MongoDB for LDA and BERTopic pipelines.
"""
import logging
from datetime import datetime
from typing import Optional

import pandas as pd

from db.connection import get_database

logger = logging.getLogger(__name__)

SUPPORTED_LANGS = ("en", "so")


async def load_tweet_corpus(
    lang: Optional[str] = None,
    limit: int = 5000,
    min_text_length: int = 5,
) -> pd.DataFrame:

    """
    Load raw tweets from MongoDB into a DataFrame for model training.

    Args:
        lang: Filter by lang_api ('en', 'so'), or None for full bilingual corpus.
        limit: Maximum tweets to load (most recent first).
        min_text_length: Drop tweets shorter than this after strip.
    """
    db = await get_database()
    query = {}
    if lang and lang in SUPPORTED_LANGS:
        query["lang_api"] = lang

    cursor = (
        db["raw_tweets"]
        .find(query)
        .sort("collected_at", -1)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    if not docs:
        logger.warning("No tweets found in raw_tweets for corpus load.")
        return pd.DataFrame()

    df = pd.DataFrame(docs)
    if "text" not in df.columns:
        return pd.DataFrame()

    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"].str.len() >= min_text_length].copy()

    for col in ("like_count", "retweet_count"):
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    if "lang_api" not in df.columns:
        df["lang_api"] = "und"

    if "created_at" not in df.columns:
        df["created_at"] = datetime.utcnow()

    logger.info("Loaded corpus: %d tweets (lang filter=%s)", len(df), lang or "all")
    return df


async def get_corpus_count(lang: Optional[str] = None) -> int:
    """Return number of tweets available for training."""
    db = await get_database()
    query = {}
    if lang and lang in SUPPORTED_LANGS:
        query["lang_api"] = lang
    return await db["raw_tweets"].count_documents(query)
