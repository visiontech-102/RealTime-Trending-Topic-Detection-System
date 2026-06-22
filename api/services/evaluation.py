"""
Shared intrinsic evaluation engine for LDA, NMF, and BERTopic.

There are no labels for this task, so ONLY intrinsic topic-quality metrics
are computed: C_v coherence (primary), U_Mass coherence (supporting), and
Topic Diversity (proportion of unique words across topics). Perplexity is
LDA-only and is never used in the three-way comparison.

All three models are scored against the SAME reference corpus and the SAME
number of top words per topic (TOP_N_WORDS), split three ways per language
(English / Somali / combined) so bilingual performance is directly visible
and directly comparable across models.
"""
import logging
from pathlib import Path

import pandas as pd

# Import before gensim: lda_model applies the scipy.linalg.triu compatibility
# patch gensim needs on scipy >= 1.13, and must run first.
from services.lda_model import preprocess_lda
from services.nmf_model import calculate_topic_diversity

from gensim.corpora import Dictionary
from gensim.models.coherencemodel import CoherenceModel

logger = logging.getLogger(__name__)

TOP_N_WORDS = 10  # SAME top-word count used for every model and every language slice
LANGUAGES = ("en", "so", "combined")


def build_reference_corpora(df: pd.DataFrame, text_col: str = "text", lang_col: str = "lang_api") -> dict:
    """
    Tokenizes ONE source corpus into three reference corpora (English,
    Somali, combined) using the SAME language-aware tokenization
    (preprocess_lda) for all three models' evaluation — regardless of which
    preprocessing each model trained on. This is the common yardstick.
    """
    tokenized = {"en": [], "so": [], "combined": []}
    for _, row in df.iterrows():
        lang = row.get(lang_col, "en")
        if lang not in ("en", "so"):
            lang = "en"
        tokens = preprocess_lda(str(row.get(text_col, "")), lang)
        if not tokens:
            continue
        tokenized["combined"].append(tokens)
        tokenized[lang].append(tokens)
    return tokenized


def build_reference_dictionary(reference_corpora: dict) -> Dictionary:
    """
    One permissive (unfiltered) dictionary built from the combined reference
    corpus, shared across all three models' coherence scoring, so every
    topic word any model produces has the best chance of resolving to an id.
    """
    return Dictionary(reference_corpora["combined"])


def _filter_topics_to_vocab(topics: list, dictionary: Dictionary) -> list:
    """Drops topic words the reference dictionary never saw (logs how many)."""
    vocab = set(dictionary.token2id.keys())
    filtered = []
    dropped = 0
    for topic in topics:
        kept = [w for w in topic if w in vocab]
        dropped += len(topic) - len(kept)
        filtered.append(kept)
    if dropped:
        logger.warning("Dropped %d topic words not present in reference vocabulary.", dropped)
    return filtered


def compute_coherence(topics: list, tokenized_docs: list, dictionary: Dictionary):
    """
    C_v (primary) and U_Mass (supporting) coherence for a list of top-word
    topics, scored against the given reference corpus.

    processes=1: gensim's default multiprocessing pool deadlocks on Windows
    when invoked without a __main__ guard (same issue fixed in lda_model.py).
    """
    topics = [t for t in topics if len(t) >= 2]
    if not topics or not tokenized_docs:
        return None, None

    cv_model = CoherenceModel(
        topics=topics,
        texts=tokenized_docs,
        dictionary=dictionary,
        coherence="c_v",
        processes=1,
    )
    cv_score = cv_model.get_coherence()

    corpus_bow = [dictionary.doc2bow(doc) for doc in tokenized_docs]
    umass_model = CoherenceModel(
        topics=topics,
        corpus=corpus_bow,
        dictionary=dictionary,
        coherence="u_mass",
        processes=1,
    )
    umass_score = umass_model.get_coherence()
    return cv_score, umass_score


def evaluate_model(model_name: str, topics: list, num_topics: int, reference_corpora: dict, dictionary: Dictionary) -> list:
    """
    Scores one model's topics three ways (en / so / combined) against the
    SAME reference corpus and SAME top-N word count used for every model.
    Returns one result row per language: {model, language, c_v, u_mass, diversity, K}.
    """
    rows = []
    for language in LANGUAGES:
        ref_docs = reference_corpora[language]
        topics_in_vocab = _filter_topics_to_vocab(topics, dictionary)

        if language == "combined":
            coherence_topics = topics_in_vocab
            diversity_topics = topics
        else:
            # Per-language filter: strip words absent from this slice's reference docs
            # before coherence scoring. Without this, topic words from the other language
            # (e.g. Somali words when scoring the English slice) have zero window-count →
            # PMI denominator = 0 → log(∞) → ∞/∞ = NaN in C_v's cosine similarity.
            # U_Mass avoids NaN via its ZeroDivisionError catch, but C_v does not.
            lang_vocab = {w for doc in ref_docs for w in doc}
            coherence_topics = [[w for w in t if w in lang_vocab] for t in topics_in_vocab]
            diversity_topics = [[w for w in t if w in lang_vocab] for t in topics]

        c_v, u_mass = compute_coherence(coherence_topics, ref_docs, dictionary)

        if c_v is None and language != "combined":
            logger.warning(
                "Model '%s' language '%s': C_v coherence is None "
                "(%d reference docs — corpus too sparse for this language slice).",
                model_name, language, len(ref_docs),
            )

        diversity = calculate_topic_diversity(diversity_topics)

        rows.append({
            "model": model_name,
            "language": language,
            "c_v": _safe_round(c_v),
            "u_mass": _safe_round(u_mass),
            "diversity": _safe_round(diversity),
            "K": num_topics,
        })
    return rows


def _safe_round(value, ndigits: int = 4):
    """
    None-safe AND NaN-safe rounding. Coherence scores can degenerate to NaN
    on very sparse reference corpora (e.g. a topic's words never co-occurring
    within a small language slice) — store None rather than a silent NaN.
    """
    if value is None or pd.isna(value):
        return None
    return round(value, ndigits)


def get_lda_topics(model, num_words: int = TOP_N_WORDS) -> list:
    """Top-word lists for every LDA topic (gensim LdaModel)."""
    return [[w for w, _ in model.show_topic(tid, topn=num_words)] for tid in range(model.num_topics)]


def get_nmf_topics(trainer, num_words: int = TOP_N_WORDS) -> list:
    """Top-word lists for every NMF topic (NMFTrainer)."""
    return trainer.get_topics(num_words=num_words)


def get_bertopic_topics(topic_model, num_words: int = TOP_N_WORDS) -> list:
    """
    Top-word lists for every BERTopic topic, excluding the -1 outlier topic
    (same convention as BERTopicTrainer.calculate_topic_diversity). Accepts
    any object exposing BERTopic's get_topics()/get_topic() interface.
    """
    topic_ids = [tid for tid in topic_model.get_topics().keys() if tid != -1]
    return [[w for w, _ in topic_model.get_topic(tid)[:num_words]] for tid in topic_ids]


def save_metrics_table(rows: list, metrics_dir: Path) -> dict:
    """
    Writes one row per (model, language) — columns: model, language, c_v,
    u_mass, diversity, K — to both CSV and JSON. Returns the saved paths.
    """
    metrics_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows, columns=["model", "language", "c_v", "u_mass", "diversity", "K"])

    csv_path = metrics_dir / "coherence_diversity.csv"
    json_path = metrics_dir / "coherence_diversity.json"
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2)

    return {"csv": csv_path, "json": json_path}


def save_topic_words(model_name: str, topics: list, reference_corpora: dict, topics_dir: Path) -> dict:
    """
    Saves the top words per topic for one model, three ways (en / so /
    combined), as long-format CSV: columns [topic_id, rank, word].
    """
    topics_dir.mkdir(parents=True, exist_ok=True)
    saved_paths = {}
    for language in LANGUAGES:
        if language == "combined":
            lang_vocab = None
        else:
            lang_vocab = {w for doc in reference_corpora[language] for w in doc}

        rows = []
        for topic_id, words in enumerate(topics):
            filtered_words = [w for w in words if lang_vocab is None or w in lang_vocab]
            for rank, word in enumerate(filtered_words, start=1):
                rows.append({"topic_id": topic_id, "rank": rank, "word": word})

        path = topics_dir / f"{model_name}_{language}_topics.csv"
        pd.DataFrame(rows, columns=["topic_id", "rank", "word"]).to_csv(path, index=False)
        saved_paths[language] = path
    return saved_paths
