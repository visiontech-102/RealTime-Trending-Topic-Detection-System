"""
Three-way metrics-driven comparison of LDA, NMF, and BERTopic.
Winner selected by highest mean C_v coherence (primary) and topic diversity (tiebreak)
across English / Somali / combined language slices — no qualitative or hardcoded logic.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from db.connection import get_database

logger = logging.getLogger(__name__)

API_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = API_ROOT / "reports" / "comparison"
EVAL_METRICS_PATH = API_ROOT / "results" / "metrics" / "coherence_diversity.json"

def _load_evaluation_metrics() -> list:
    """
    Reads the three-way metrics written by run_evaluation.py.
    Returns an empty list (not an error) if the evaluation has not been run yet.
    """
    if not EVAL_METRICS_PATH.exists():
        logger.warning(
            "Evaluation metrics file not found at %s — "
            "run `python run_evaluation.py` first for objective winner selection.",
            EVAL_METRICS_PATH,
        )
        return []
    with EVAL_METRICS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _select_winner_from_metrics(rows: list) -> tuple:
    """
    Chooses the best model from coherence_diversity.json rows.

    Primary  : highest mean C_v coherence across all language slices
               (en / so / combined).  None values are skipped so a sparse
               language slice does not unfairly penalise any model.
    Tie-break: highest mean topic diversity across the same rows.

    Returns (winner: str | None, scores: dict).  Returns (None, {}) when rows
    is empty so callers can detect that no real metrics exist and skip
    deployment — a winner is NEVER chosen without measured data.
    """
    if not rows:
        return None, {}

    from collections import defaultdict

    cv_by_model: dict = defaultdict(list)
    div_by_model: dict = defaultdict(list)
    for row in rows:
        m = row["model"]
        if row.get("c_v") is not None:
            cv_by_model[m].append(row["c_v"])
        if row.get("diversity") is not None:
            div_by_model[m].append(row["diversity"])

    def _mean(lst):
        return sum(lst) / len(lst) if lst else -1.0

    models = list({r["model"] for r in rows})
    ranked = sorted(
        models,
        key=lambda m: (_mean(cv_by_model[m]), _mean(div_by_model[m])),
        reverse=True,
    )

    scores = {
        m: {
            "mean_c_v": round(_mean(cv_by_model[m]), 4),
            "mean_diversity": round(_mean(div_by_model[m]), 4),
        }
        for m in models
    }
    winner = ranked[0]
    logger.info(
        "Winner selection — scores: %s → winner: %s",
        scores,
        winner,
    )
    return winner, scores


def _build_per_model_metrics(rows: list) -> dict:
    """
    Reshapes coherence_diversity.json rows into
    {model: {language: {c_v, u_mass, diversity, K}}}.
    All values come from the SAME evaluation run on the SAME corpus, so every
    number in the comparison report shares a single provenance.
    """
    result: dict = {}
    for row in rows:
        m = row["model"]
        lang = row["language"]
        result.setdefault(m, {})[lang] = {
            "c_v": row.get("c_v"),
            "u_mass": row.get("u_mass"),
            "diversity": row.get("diversity"),
            "K": row.get("K"),
        }
    return result


async def run_model_comparison() -> dict:
    """
    Aggregate latest LDA, NMF, and BERTopic pipeline runs into a comparison report.
    Does not re-train models unless metrics are missing (caller should run jobs first).
    """
    db = await get_database()
    lda_state = await db["pipeline_state"].find_one({"pipeline": "lda"})
    nmf_state = await db["pipeline_state"].find_one({"pipeline": "nmf"})
    bertopic_state = await db["pipeline_state"].find_one({"pipeline": "bertopic"})

    if not (lda_state and nmf_state and bertopic_state):
        missing = [m for m, s in [("lda", lda_state), ("nmf", nmf_state), ("bertopic", bertopic_state)] if not s]
        return {
            "status": "skipped",
            "reason": "incomplete_pipeline_runs",
            "missing_pipelines": missing,
            "message": "All three pipelines must have run before comparison. Missing: " + ", ".join(missing),
        }

    # Objective winner selection from three-way evaluation metrics.
    eval_rows = _load_evaluation_metrics()
    winner, metric_scores = _select_winner_from_metrics(eval_rows)

    if winner is None:
        return {
            "status": "skipped",
            "reason": "evaluation_not_run",
            "message": (
                "No evaluation metrics found. "
                "Run `python run_evaluation.py` (or POST /jobs/run-evaluation) "
                "before running the comparison."
            ),
        }

    per_model = _build_per_model_metrics(eval_rows)

    calculated_at = datetime.now(timezone.utc)
    report = {
        "generated_at": calculated_at.isoformat(),
        "selected_deployment_model": winner,
        "winner_selection_basis": "metrics",
        "winner_selection_rule": "primary=mean_c_v, tiebreak=mean_diversity (across en/so/combined)",
        "model_metric_scores": metric_scores,
        "academic_note": "LDA and NMF retained as baselines per FYP Implementation Plan Part 6.",
        "lda_metrics": per_model.get("lda"),
        "nmf_metrics": per_model.get("nmf"),
        "bertopic_metrics": per_model.get("bertopic"),
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "latest_comparison.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    await db["pipeline_state"].update_one(
        {"pipeline": "model_comparison"},
        {"$set": {"last_run_at": calculated_at, "report": report}},
        upsert=True,
    )

    from jobs.deployment import persist_deployed_model
    await persist_deployed_model(winner)

    logger.info("Model comparison saved. Winner: %s, scores: %s", winner, metric_scores)
    return {"status": "success", "report_path": str(report_path), **report}
