"""
Enhancement stage: after run_full_evaluation() selects a winner, run_enhancement()
tunes ONLY that model's hyperparameters over a small grid, re-evaluates with the
exact same evaluate_model() functions (same corpus load, same reference dictionary,
same TOP_N_WORDS, same en/so/combined slices, same random seeds), and records a
structured before/after comparison in results/enhancement/before_after.json.

The enhanced config is marked adopted=True only when the best candidate's mean C_v
strictly exceeds the baseline. If no candidate beats the baseline the original
config is kept and adopted=False is written — the baseline is never discarded.

The two losing models are never touched. No evaluation or model-service files are
modified.

BERTopic timing note: each BERTopic candidate requires a full SentenceTransformer
encoding pass (~2-5 min on CPU for 2 000 docs) plus UMAP/HDBSCAN/coherence scoring
(~1 min). Three candidates therefore take roughly 10-20 min on CPU, 3-7 min with
GPU encoding.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sklearn.decomposition import NMF as SklearnNMF

from jobs.bertopic_pipeline import _adaptive_min_cluster_size
from jobs.lda_pipeline import CORPUS_LIMIT, MIN_CORPUS_SIZE, _tokenize_corpus
from pipelines.corpus_loader import get_corpus_count, load_tweet_corpus
from services.bertopic_model import BERTopicTrainer, preprocess_bertopic
from services.evaluation import (
    TOP_N_WORDS,
    build_reference_corpora,
    build_reference_dictionary,
    evaluate_model,
    get_bertopic_topics,
    get_lda_topics,
    get_nmf_topics,
)
from services.lda_model import LDATrainer, prepare_lda_matrices
from services.nmf_model import NMFTrainer, prepare_nmf_matrix

logger = logging.getLogger(__name__)

API_ROOT          = Path(__file__).resolve().parent.parent
EVAL_METRICS_PATH = API_ROOT / "results" / "metrics" / "coherence_diversity.json"
ENHANCEMENT_DIR   = API_ROOT / "results" / "enhancement"

# ---------------------------------------------------------------------------
# Hyperparameter grids
# ---------------------------------------------------------------------------

# LDA: 2 × 2 × 2 = 8 candidates (the current default is always candidate #1)
LDA_ALPHA_RANGE  = ["symmetric", "auto"]  # prior concentration; "auto" learns per-doc
LDA_ETA_RANGE    = ["symmetric", "auto"]  # per-topic word prior; "auto" learns per-topic
LDA_PASSES_RANGE = [10, 20]              # extra passes help on small corpora

# NMF: 2 × 2 = 4 candidates
# max_features excluded: prepare_nmf_matrix fixes vocab to the gensim Dictionary,
# so varying it would require touching that function.
NMF_INIT_RANGE    = ["nndsvda", "nndsvd"]  # nndsvd is sparser → sometimes sharper topics
NMF_MAXITER_RANGE = [400, 600]

# BERTopic: ≤3 candidates (de-duped; all capped at min 3).
# ngram_range excluded: BERTopicTrainer.__init__ builds CountVectorizer with no
# ngram_range param; varying it would require modifying the constructor.
BERTOPIC_MCS_OFFSETS = [0, 2, 4]  # added to the adaptive base min_cluster_size


# ---------------------------------------------------------------------------
# Pure helpers — no DB, no model I/O
# ---------------------------------------------------------------------------

def _safe_mean(vals: list):
    """Mean of a list, skipping None values; returns Python float or None."""
    clean = [float(v) for v in vals if v is not None]
    return sum(clean) / len(clean) if clean else None


def _baseline_stats(eval_rows: list, model: str) -> tuple:
    """Return (mean_c_v, mean_diversity) for one model from eval_rows."""
    cv  = _safe_mean([r.get("c_v")       for r in eval_rows if r["model"] == model])
    div = _safe_mean([r.get("diversity") for r in eval_rows if r["model"] == model])
    return cv, div


def _get_k(eval_rows: list, model: str) -> int:
    """Return the K used during evaluation for this model (falls back to 8)."""
    for r in eval_rows:
        if r["model"] == model and r.get("K"):
            return int(r["K"])
    return 8


def _rank_candidates(candidates: list) -> list:
    """Sort by (mean_c_v desc, mean_diversity desc); None values sort last."""
    return sorted(
        candidates,
        key=lambda c: (
            c["mean_c_v"]       if c["mean_c_v"]       is not None else -1.0,
            c["mean_diversity"] if c["mean_diversity"] is not None else -1.0,
        ),
        reverse=True,
    )


# ---------------------------------------------------------------------------
# Per-model synchronous sweeps
# (called via asyncio.to_thread so they don't block the event loop)
# ---------------------------------------------------------------------------

def _sweep_lda(tokenized_docs: list, k: int,
               reference_corpora: dict, ref_dictionary) -> list:
    """
    8-candidate sweep: alpha × eta × passes at the K selected by evaluation.
    Uses the same LDATrainer / evaluate_model() as evaluation_pipeline.py;
    random_state=42 is hardcoded inside LdaModel (lda_model.py:136).
    """
    lda_dict, corpus_bow = prepare_lda_matrices(tokenized_docs, use_tfidf=False)
    candidates = []
    for alpha in LDA_ALPHA_RANGE:
        for eta in LDA_ETA_RANGE:
            for passes in LDA_PASSES_RANGE:
                trainer = LDATrainer(lda_dict, corpus_bow)
                trainer.train(num_topics=k, alpha=alpha, eta=eta, passes=passes)
                topics = get_lda_topics(trainer.model, num_words=TOP_N_WORDS)
                rows   = evaluate_model("lda", topics, k, reference_corpora, ref_dictionary)
                candidates.append({
                    "config": {"alpha": alpha, "eta": eta, "passes": passes, "K": k},
                    "rows":           rows,
                    "mean_c_v":       _safe_mean([r.get("c_v")       for r in rows]),
                    "mean_diversity": _safe_mean([r.get("diversity") for r in rows]),
                })
    return _rank_candidates(candidates)


def _sweep_nmf(tokenized_docs: list, k: int,
               reference_corpora: dict, ref_dictionary) -> list:
    """
    4-candidate sweep: init × max_iter at the K selected by evaluation.
    TF-IDF matrix is built once (same dictionary, same docs → identical for all
    candidates). SklearnNMF is constructed directly so init/max_iter can be
    varied without modifying NMFTrainer.train(), which hardcodes them.
    random_state=42 passed explicitly to match evaluation.
    """
    lda_dict, _       = prepare_lda_matrices(tokenized_docs, use_tfidf=False)
    tfidf_matrix, vec = prepare_nmf_matrix(tokenized_docs, lda_dict)
    candidates = []
    for init in NMF_INIT_RANGE:
        for max_iter in NMF_MAXITER_RANGE:
            trainer       = NMFTrainer(tfidf_matrix, vec)
            trainer.model = SklearnNMF(
                n_components=k, init=init, max_iter=max_iter, random_state=42
            )
            trainer.model.fit(tfidf_matrix)
            topics = get_nmf_topics(trainer, num_words=TOP_N_WORDS)
            rows   = evaluate_model("nmf", topics, k, reference_corpora, ref_dictionary)
            candidates.append({
                "config": {"init": init, "max_iter": max_iter, "K": k},
                "rows":           rows,
                "mean_c_v":       _safe_mean([r.get("c_v")       for r in rows]),
                "mean_diversity": _safe_mean([r.get("diversity") for r in rows]),
            })
    return _rank_candidates(candidates)


def _sweep_bertopic(df_clean, base_mcs: int,
                    reference_corpora: dict, ref_dictionary) -> list:
    """
    ≤3-candidate sweep over min_cluster_size offsets from the adaptive base.
    UMAP random_state=42 is hardcoded in BERTopicTrainer.__init__() (bertopic_model.py:49).
    """
    mcs_values = sorted({max(3, base_mcs + off) for off in BERTOPIC_MCS_OFFSETS})
    docs       = df_clean["clean_text"].tolist()
    candidates = []
    for mcs in mcs_values:
        try:
            trainer            = BERTopicTrainer(min_cluster_size=mcs)
            topics_assigned, _ = trainer.train(docs)
            trainer._training_docs = docs  # noqa: SLF001 — mirrors _run_training_sync
            bt_topics = get_bertopic_topics(trainer.topic_model, num_words=TOP_N_WORDS)
            n_topics  = len(bt_topics)
            rows      = evaluate_model("bertopic", bt_topics, n_topics, reference_corpora, ref_dictionary)
            candidates.append({
                "config": {"min_cluster_size": mcs},
                "rows":           rows,
                "mean_c_v":       _safe_mean([r.get("c_v")       for r in rows]),
                "mean_diversity": _safe_mean([r.get("diversity") for r in rows]),
            })
        except Exception:
            logger.warning("BERTopic sweep candidate mcs=%d failed — skipping.", mcs, exc_info=True)
            continue
    return _rank_candidates(candidates)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_enhancement(winner: str) -> dict:
    """
    Tune ONLY the winning model. Guaranteed invariants vs the original evaluation:
      - Same CORPUS_LIMIT, same load_tweet_corpus() call.
      - Same build_reference_corpora() + build_reference_dictionary() on the same df.
      - Same evaluate_model() with same TOP_N_WORDS and same LANGUAGES slice.
      - Same random seeds in all three model types (see sweep function docstrings).
    """
    # 1. Load baseline from the file evaluation wrote
    if not EVAL_METRICS_PATH.exists():
        logger.warning("Enhancement skipped — metrics file not found at %s", EVAL_METRICS_PATH)
        return {"status": "skipped", "reason": "no_evaluation_metrics"}

    with EVAL_METRICS_PATH.open(encoding="utf-8") as f:
        eval_rows = json.load(f)

    baseline_cv, baseline_diversity = _baseline_stats(eval_rows, winner)

    if baseline_cv is None:
        logger.warning("Enhancement skipped — no C_v baseline for winner '%s'", winner)
        return {"status": "skipped", "reason": "winner_has_no_baseline_c_v", "winner": winner}

    # 2. Load corpus — same parameters as evaluation
    count = await get_corpus_count()
    if count < MIN_CORPUS_SIZE:
        return {"status": "skipped", "reason": "insufficient_corpus", "corpus_count": count}

    df = await load_tweet_corpus(lang=None, limit=CORPUS_LIMIT)
    if df.empty:
        return {"status": "skipped", "reason": "empty_corpus"}

    # 3. Reference corpora + dictionary — same functions as evaluation_pipeline.py
    reference_corpora = build_reference_corpora(df)
    ref_dictionary    = build_reference_dictionary(reference_corpora)

    # 4. Sweep the winning model only
    k = _get_k(eval_rows, winner)

    if winner == "lda":
        tokenized_docs = _tokenize_corpus(df)
        ranked = await asyncio.to_thread(
            _sweep_lda, tokenized_docs, k, reference_corpora, ref_dictionary
        )
    elif winner == "nmf":
        tokenized_docs = _tokenize_corpus(df)
        ranked = await asyncio.to_thread(
            _sweep_nmf, tokenized_docs, k, reference_corpora, ref_dictionary
        )
    elif winner == "bertopic":
        df_clean = preprocess_bertopic(df, text_col="text")
        base_mcs = _adaptive_min_cluster_size(len(df_clean))
        ranked   = await asyncio.to_thread(
            _sweep_bertopic, df_clean, base_mcs, reference_corpora, ref_dictionary
        )
    else:
        return {"status": "skipped", "reason": "unknown_winner", "winner": winner}

    if not ranked:
        return {"status": "skipped", "reason": "empty_sweep_results"}

    best    = ranked[0]
    best_cv = best["mean_c_v"]
    adopted = bool(best_cv is not None and best_cv > baseline_cv)

    # 5. Build and persist the before/after report
    report = {
        "winner":       winner,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline": {
            "mean_c_v":       round(baseline_cv, 4),
            "mean_diversity": round(baseline_diversity, 4) if baseline_diversity is not None else None,
        },
        "enhanced": {
            "mean_c_v":       round(best_cv, 4) if best_cv is not None else None,
            "mean_diversity": round(best["mean_diversity"], 4) if best["mean_diversity"] is not None else None,
        },
        "delta_c_v": round(best_cv - baseline_cv, 4) if best_cv is not None else None,
        "delta_diversity": (
            round(best["mean_diversity"] - baseline_diversity, 4)
            if best["mean_diversity"] is not None and baseline_diversity is not None
            else None
        ),
        "adopted":        adopted,
        "adopted_config": best["config"] if adopted else None,
        "all_candidates": [
            {
                "config":         c["config"],
                "mean_c_v":       round(c["mean_c_v"],       4) if c["mean_c_v"]       is not None else None,
                "mean_diversity": round(c["mean_diversity"], 4) if c["mean_diversity"] is not None else None,
            }
            for c in ranked
        ],
    }

    ENHANCEMENT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ENHANCEMENT_DIR / "before_after.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    logger.info(
        "Enhancement complete. winner=%s baseline_cv=%.4f best_cv=%.4f adopted=%s config=%s",
        winner, baseline_cv, best_cv or 0.0, adopted,
        best["config"] if adopted else "none",
    )
    return {"status": "success", "report_path": str(out_path), **report}
