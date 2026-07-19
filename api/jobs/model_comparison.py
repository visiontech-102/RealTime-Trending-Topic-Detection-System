"""
Three-way metrics-driven comparison of LDA, NMF, and BERTopic.

Evaluation approach (Option B — bilingual dominant-language):
  - Metrics computed separately for English and Somali slices.
  - "combined" slice is excluded: it is not an independent measurement
    (it merges en+so already captured individually) and its inclusion
    inflates bag-of-words models (NMF/LDA) via cross-lingual TF-IDF signal.
  - Winner selection: primary = English C_v (dominant language);
    tiebreak = Somali C_v.
  - No qualitative or hardcoded model preferences.
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
    Reads the three-way metrics written by run_full_evaluation().
    Returns an empty list if the evaluation has not been run yet.
    Only en and so rows are present (combined excluded at evaluation time).
    """
    if not EVAL_METRICS_PATH.exists():
        logger.warning(
            "Evaluation metrics file not found at %s — "
            "run POST /jobs/run-evaluation first.",
            EVAL_METRICS_PATH,
        )
        return []
    with EVAL_METRICS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _select_winner_from_metrics(rows: list) -> tuple:
    """
    Option B winner selection:
      Primary  : English C_v (highest wins).
      Tiebreak : Somali C_v (highest wins).
      Secondary tiebreak: English Topic Diversity (highest wins).

    'combined' rows are ignored even if present (legacy data guard).

    Returns (winner: str | None, scores: dict).
    Returns (None, {}) when rows is empty — a winner is NEVER chosen
    without measured data.
    """
    if not rows:
        return None, {}

    cv: dict = {}    # model → {lang: c_v}
    div: dict = {}   # model → {lang: diversity}

    for row in rows:
        m, lang = row["model"], row["language"]
        if lang not in ("en", "so"):
            continue
        cv.setdefault(m, {})[lang] = row.get("c_v")
        div.setdefault(m, {})[lang] = row.get("diversity")

    models = list(cv.keys())
    if not models:
        return None, {}

    def _get(d, model, lang):
        return d.get(model, {}).get(lang) or -1.0

    ranked = sorted(
        models,
        key=lambda m: (
            _get(cv, m, "en"),   # primary: English C_v
            _get(cv, m, "so"),   # tiebreak: Somali C_v
            _get(div, m, "en"),  # secondary tiebreak: English diversity
        ),
        reverse=True,
    )

    scores = {
        m: {
            "en_c_v":        cv.get(m, {}).get("en"),
            "so_c_v":        cv.get(m, {}).get("so"),
            "en_diversity":  div.get(m, {}).get("en"),
            "so_diversity":  div.get(m, {}).get("so"),
        }
        for m in models
    }
    winner = ranked[0]
    logger.info("Winner selection (en C_v primary, so C_v tiebreak) — scores: %s → winner: %s", scores, winner)
    return winner, scores


def _build_per_model_metrics(rows: list) -> dict:
    """
    Reshapes coherence_diversity.json rows into
    {model: {language: {c_v, u_mass, diversity, K}}}.
    Only en and so slices are included (combined excluded).
    """
    result: dict = {}
    for row in rows:
        m, lang = row["model"], row["language"]
        if lang not in ("en", "so"):
            continue
        result.setdefault(m, {})[lang] = {
            "c_v":       row.get("c_v"),
            "u_mass":    row.get("u_mass"),
            "diversity": row.get("diversity"),
            "K":         row.get("K"),
        }
    return result


async def run_model_comparison() -> dict:
    """
    Aggregate latest LDA, NMF, and BERTopic pipeline runs into a comparison
    report using Option B evaluation (en + so, English primary).
    """
    db = await get_database()
    lda_state      = await db["pipeline_state"].find_one({"pipeline": "lda"})
    nmf_state      = await db["pipeline_state"].find_one({"pipeline": "nmf"})
    bertopic_state = await db["pipeline_state"].find_one({"pipeline": "bertopic"})

    if not (lda_state and nmf_state and bertopic_state):
        missing = [
            m for m, s in [("lda", lda_state), ("nmf", nmf_state), ("bertopic", bertopic_state)]
            if not s
        ]
        return {
            "status": "skipped",
            "reason": "incomplete_pipeline_runs",
            "missing_pipelines": missing,
            "message": "All three pipelines must have run. Missing: " + ", ".join(missing),
        }

    eval_rows = _load_evaluation_metrics()
    winner, metric_scores = _select_winner_from_metrics(eval_rows)

    if winner is None:
        return {
            "status": "skipped",
            "reason": "evaluation_not_run",
            "message": "No evaluation metrics found. Run POST /jobs/run-evaluation first.",
        }

    per_model = _build_per_model_metrics(eval_rows)
    calculated_at = datetime.now(timezone.utc)

    report = {
        "generated_at":              calculated_at.isoformat(),
        "selected_deployment_model": winner,
        "winner_selection_basis":    "intrinsic metrics",
        "winner_selection_rule":     (
            "primary=English C_v (dominant language); "
            "tiebreak=Somali C_v; combined slice excluded (not independent)"
        ),
        "model_metric_scores":  metric_scores,
        "academic_note": (
            "Evaluation: C_v coherence and Topic Diversity scored separately "
            "on English and Somali slices of the same corpus. "
            "LDA and NMF are retained as baselines per FYP Implementation Plan Part 6."
        ),
        "lda_metrics":      per_model.get("lda"),
        "nmf_metrics":      per_model.get("nmf"),
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

    logger.info("Model comparison saved. Winner: %s", winner)
    return {"status": "success", "report_path": str(report_path), **report}
