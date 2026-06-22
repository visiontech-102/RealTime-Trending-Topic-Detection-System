"""
Sandbox verification for the shared three-way evaluation engine, using
synthetic dummy data only. Does not touch MongoDB / raw_tweets and does not
train a real BERTopic (no network/model download) — a mock object exposing
BERTopic's get_topics()/get_topic() interface stands in for it.
"""
import pandas as pd

from services.evaluation import (
    LANGUAGES,
    TOP_N_WORDS,
    build_reference_corpora,
    build_reference_dictionary,
    compute_coherence,
    evaluate_model,
    get_bertopic_topics,
    get_lda_topics,
    get_nmf_topics,
    save_metrics_table,
    save_topic_words,
)
from services.lda_model import LDATrainer, prepare_lda_matrices
from services.nmf_model import NMFTrainer, prepare_nmf_matrix


class _MockBERTopicModel:
    """Mimics BERTopic's get_topics()/get_topic() interface, including the -1 outlier."""

    def __init__(self, topics_by_id):
        self._topics_by_id = topics_by_id

    def get_topics(self):
        return self._topics_by_id

    def get_topic(self, topic_id):
        return self._topics_by_id[topic_id]


def _synthetic_bilingual_df():
    rows = []
    en_sports = "football match goal team player league score"
    en_politics = "election government minister parliament vote policy"
    so_sports = "kubadda ciyaar kooxda horyaal ciyaartoy"
    so_politics = "dowlad doorasho baarlamaan wasiir siyaasad"
    for _ in range(15):
        rows.append({"text": en_sports, "lang_api": "en"})
        rows.append({"text": en_politics, "lang_api": "en"})
        rows.append({"text": so_sports, "lang_api": "so"})
        rows.append({"text": so_politics, "lang_api": "so"})
    return pd.DataFrame(rows)


def test_build_reference_corpora_splits_by_language():
    df = _synthetic_bilingual_df()
    corpora = build_reference_corpora(df)

    assert set(corpora.keys()) == {"en", "so", "combined"}
    assert len(corpora["en"]) == 30
    assert len(corpora["so"]) == 30
    assert len(corpora["combined"]) == 60
    # no stemming / no cross-language leakage: somali tokens never end up in 'en'
    so_only_words = {"kubadda", "dowlad", "wasiir"}
    en_words = {w for doc in corpora["en"] for w in doc}
    assert not (so_only_words & en_words)


def test_build_reference_dictionary_covers_combined_vocab():
    df = _synthetic_bilingual_df()
    corpora = build_reference_corpora(df)
    dictionary = build_reference_dictionary(corpora)

    all_words = {w for doc in corpora["combined"] for w in doc}
    assert all_words.issubset(set(dictionary.token2id.keys()))


def test_compute_coherence_returns_scores_for_valid_topics():
    df = _synthetic_bilingual_df()
    corpora = build_reference_corpora(df)
    dictionary = build_reference_dictionary(corpora)

    topics = [["football", "match", "goal"], ["election", "government", "vote"]]
    cv, umass = compute_coherence(topics, corpora["combined"], dictionary)

    assert cv is not None and umass is not None
    assert 0.0 <= cv <= 1.0
    assert umass <= 1e-9  # u_mass is non-positive by definition (tiny float fuzz tolerated)


def test_compute_coherence_empty_topics_returns_none():
    df = _synthetic_bilingual_df()
    corpora = build_reference_corpora(df)
    dictionary = build_reference_dictionary(corpora)
    cv, umass = compute_coherence([], corpora["combined"], dictionary)
    assert cv is None and umass is None


def test_evaluate_model_produces_one_row_per_language():
    df = _synthetic_bilingual_df()
    corpora = build_reference_corpora(df)
    dictionary = build_reference_dictionary(corpora)

    topics = [
        ["football", "match", "goal", "team"],
        ["dowlad", "doorasho", "wasiir", "siyaasad"],
    ]
    rows = evaluate_model("dummy_model", topics, num_topics=2, reference_corpora=corpora, dictionary=dictionary)

    assert len(rows) == 3
    assert {r["language"] for r in rows} == set(LANGUAGES)
    for r in rows:
        assert r["model"] == "dummy_model"
        assert r["K"] == 2
        assert set(r.keys()) == {"model", "language", "c_v", "u_mass", "diversity", "K"}


def test_lda_and_nmf_topic_extraction_share_same_top_n():
    df = _synthetic_bilingual_df()
    corpora = build_reference_corpora(df)
    tokenized_docs = corpora["combined"]

    dictionary, corpus = prepare_lda_matrices(tokenized_docs, use_tfidf=False)
    lda_trainer = LDATrainer(dictionary, corpus)
    lda_trainer.train(num_topics=2, passes=5)
    lda_topics = get_lda_topics(lda_trainer.model)

    tfidf_matrix, vectorizer = prepare_nmf_matrix(tokenized_docs, dictionary)
    nmf_trainer = NMFTrainer(tfidf_matrix, vectorizer)
    nmf_trainer.train(num_topics=2)
    nmf_topics = get_nmf_topics(nmf_trainer)

    assert len(lda_topics) == 2 and len(nmf_topics) == 2
    assert all(len(t) <= TOP_N_WORDS for t in lda_topics + nmf_topics)


def test_get_bertopic_topics_excludes_outlier_and_respects_top_n():
    mock_model = _MockBERTopicModel({
        -1: [("noise", 0.1), ("misc", 0.05)],
        0: [(w, 1.0 - i * 0.1) for i, w in enumerate(
            ["football", "match", "goal", "team", "player", "league", "score", "win", "cup", "draw", "extra"]
        )],
        1: [("election", 0.9), ("government", 0.8), ("vote", 0.7)],
    })

    topics = get_bertopic_topics(mock_model, num_words=10)

    assert len(topics) == 2  # -1 excluded
    assert len(topics[0]) == 10  # truncated to TOP_N_WORDS
    assert "noise" not in [w for t in topics for w in t]


def test_save_metrics_table_writes_csv_and_json(tmp_path):
    rows = [
        {"model": "lda", "language": "en", "c_v": 0.4, "u_mass": -1.2, "diversity": 0.8, "K": 8},
        {"model": "lda", "language": "so", "c_v": 0.35, "u_mass": -1.5, "diversity": 0.75, "K": 8},
    ]
    saved = save_metrics_table(rows, tmp_path)

    assert saved["csv"].exists()
    assert saved["json"].exists()
    df = pd.read_csv(saved["csv"])
    assert list(df.columns) == ["model", "language", "c_v", "u_mass", "diversity", "K"]
    assert len(df) == 2


def test_save_topic_words_writes_per_language_csv(tmp_path):
    df = _synthetic_bilingual_df()
    corpora = build_reference_corpora(df)
    topics = [["football", "match", "dowlad"], ["election", "kubadda"]]

    saved = save_topic_words("dummy_model", topics, corpora, tmp_path)

    assert set(saved.keys()) == set(LANGUAGES)
    en_df = pd.read_csv(saved["en"])
    so_df = pd.read_csv(saved["so"])
    combined_df = pd.read_csv(saved["combined"])

    assert set(en_df["word"]) == {"football", "match", "election"}
    assert set(so_df["word"]) == {"dowlad", "kubadda"}
    assert set(combined_df["word"]) == {"football", "match", "dowlad", "election", "kubadda"}
