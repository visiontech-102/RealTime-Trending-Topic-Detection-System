"""
Builds LDA vs BERTopic comparison from latest pipeline_state metrics (Plan Part 5).
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from db.connection import get_database

logger = logging.getLogger(__name__)

API_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = API_ROOT / "reports" / "comparison"

# Eight criteria from FYP Implementation Plan §5.2
CRITERIA = [
    "architecture",
    "preprocessing",
    "semantic_understanding",
    "multilingual_capability",
    "short_text_performance",
    "real_time_suitability",
    "compute_requirements",
    "topic_novelty",
]


def _build_criteria_table(lda: dict, bertopic: dict) -> list:
    lda_metrics = lda.get("metrics") or {}
    bt_metrics = bertopic.get("metrics") or {}

    coherence = lda_metrics.get("coherence_cv")
    perplexity = lda_metrics.get("perplexity")
    cohesion = bt_metrics.get("semantic_cohesion")
    diversity = bt_metrics.get("topic_diversity")
    outlier_ratio = bt_metrics.get("outlier_ratio")

    return [
        {
            "criterion": "Architecture",
            "lda": "Generative Probabilistic (Gensim LDA)",
            "bertopic": "Modular (Embeddings + UMAP + HDBSCAN + c-TF-IDF)",
            "deployment_winner": "bertopic",
        },
        {
            "criterion": "Preprocessing",
            "lda": "Heavy (lowercase, URL/@ removal, stopwords, tokenization)",
            "bertopic": "Minimal (dedupe, preserve sentence structure)",
            "deployment_winner": "bertopic",
        },
        {
            "criterion": "Semantic Understanding",
            "lda": f"Low (BoW; coherence Cv={coherence})" if coherence else "Low (Bag-of-Words)",
            "bertopic": f"High (transformer embeddings; cohesion={cohesion})" if cohesion else "High (contextual embeddings)",
            "deployment_winner": "bertopic",
        },
        {
            "criterion": "Multilingual Capability (Somali)",
            "lda": "Requires Somali stopwords (custom list used); no unified embedding space",
            "bertopic": "Native multilingual MiniLM-L12-v2 (EN + SO unified space)",
            "deployment_winner": "bertopic",
        },
        {
            "criterion": "Short-Text Performance",
            "lda": "Poor on sparse 280-char tweets (documented baseline limitation)",
            "bertopic": "Optimised for short noisy social text",
            "deployment_winner": "bertopic",
        },
        {
            "criterion": "Real-Time Suitability",
            "lda": "Low (predefined K, retraining cost)",
            "bertopic": "High (DTM, dynamic c-TF-IDF, auto clusters)",
            "deployment_winner": "bertopic",
        },
        {
            "criterion": "Compute Requirements",
            "lda": "Moderate CPU (matrix factorisation)",
            "bertopic": "Higher (GPU recommended for embeddings)",
            "deployment_winner": "lda",
        },
        {
            "criterion": "Topic Novelty",
            "lda": f"Standard word co-occurrence topics (K={lda_metrics.get('num_topics', '—')})",
            "bertopic": f"Context-rich clusters (diversity={diversity}, outliers={outlier_ratio})",
            "deployment_winner": "bertopic",
        },
    ]


async def run_model_comparison() -> dict:
    """
    Aggregate latest LDA and BERTopic pipeline runs into a comparison report.
    Does not re-train models unless metrics are missing (caller should run jobs first).
    """
    db = await get_database()
    lda_state = await db["pipeline_state"].find_one({"pipeline": "lda"})
    bertopic_state = await db["pipeline_state"].find_one({"pipeline": "bertopic"})

    if not lda_state and not bertopic_state:
        return {
            "status": "skipped",
            "reason": "no_pipeline_runs",
            "message": "Run POST /jobs/train-lda and POST /jobs/train-bertopic first.",
        }

    criteria_table = _build_criteria_table(lda_state or {}, bertopic_state or {})
    bertopic_wins = sum(1 for row in criteria_table if row["deployment_winner"] == "bertopic")

    calculated_at = datetime.now(timezone.utc)
    report = {
        "generated_at": calculated_at.isoformat(),
        "selected_deployment_model": "bertopic",
        "academic_note": "LDA retained as baseline per FYP Implementation Plan Part 6.",
        "criteria_winner_count": {
            "bertopic": bertopic_wins,
            "lda": len(criteria_table) - bertopic_wins,
        },
        "lda_metrics": lda_state.get("metrics") if lda_state else None,
        "bertopic_metrics": bertopic_state.get("metrics") if bertopic_state else None,
        "lda_last_run": lda_state.get("last_run_at") if lda_state else None,
        "bertopic_last_run": bertopic_state.get("last_run_at") if bertopic_state else None,
        "criteria_comparison": criteria_table,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "latest_comparison.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    await db["pipeline_state"].update_one(
        {"pipeline": "model_comparison"},
        {"$set": {"last_run_at": calculated_at, "report": report}},
        upsert=True,
    )

    logger.info("Model comparison saved (%d/%d criteria favour BERTopic)", bertopic_wins, len(criteria_table))
    return {"status": "success", "report_path": str(report_path), **report}
