"""
Sandbox verification for the NMF baseline using synthetic dummy documents only.
Does not touch MongoDB / raw_tweets — these are unit tests of the NMF service
and pipeline helpers in isolation.
"""
import pandas as pd

from jobs.nmf_pipeline import _pick_best_from_grid, _run_nmf_sync, _tokenize_corpus
from services.lda_model import prepare_lda_matrices
from services.nmf_model import (
    NMFTrainer,
    calculate_topic_diversity,
    prepare_nmf_matrix,
    run_nmf_grid_search,
)

# Three synthetic "topics" worth of English tokens, repeated with noise so
# NMF/coherence have enough signal to separate clusters on a tiny corpus.
_EN_SPORTS = ["football", "match", "goal", "team", "player", "league", "score"]
_EN_POLITICS = ["election", "government", "minister", "parliament", "vote", "policy"]
_EN_TECH = ["software", "computer", "internet", "data", "server", "app"]

# Synthetic Somali tokens (post-stopword-removal shape), same three themes.
_SO_SPORTS = ["kubadda", "ciyaar", "kooxda", "horyaal", "ciyaartoy"]
_SO_POLITICS = ["dowlad", "doorasho", "baarlamaan", "wasiir", "siyaasad"]
_SO_TECH = ["internet", "tiknoolajiyad", "shabakad", "softiweer"]


def _make_tokenized_docs(theme_word_lists, n_per_theme=12):
    docs = []
    for words in theme_word_lists:
        for i in range(n_per_theme):
            # vary doc length slightly to mimic real tweets
            docs.append(words + [words[i % len(words)]])
    return docs


def _synthetic_tokenized_corpus():
    return _make_tokenized_docs([_EN_SPORTS, _EN_POLITICS, _EN_TECH, _SO_SPORTS, _SO_POLITICS, _SO_TECH])


def test_prepare_nmf_matrix_shares_lda_vocabulary():
    tokenized_docs = _synthetic_tokenized_corpus()
    dictionary, _ = prepare_lda_matrices(tokenized_docs, use_tfidf=False)

    tfidf_matrix, vectorizer = prepare_nmf_matrix(tokenized_docs, dictionary)

    assert tfidf_matrix.shape[0] == len(tokenized_docs)
    assert tfidf_matrix.shape[1] == len(dictionary.token2id)
    assert set(vectorizer.get_feature_names_out()) == set(dictionary.token2id.keys())


def test_nmf_trainer_train_and_topics():
    tokenized_docs = _synthetic_tokenized_corpus()
    dictionary, _ = prepare_lda_matrices(tokenized_docs, use_tfidf=False)
    tfidf_matrix, vectorizer = prepare_nmf_matrix(tokenized_docs, dictionary)

    trainer = NMFTrainer(tfidf_matrix, vectorizer)
    trainer.train(num_topics=6)
    topics = trainer.get_topics(num_words=5)

    assert len(topics) == 6
    assert all(len(t) <= 5 for t in topics)
    assert all(isinstance(w, str) for t in topics for w in t)


def test_nmf_trainer_evaluate_returns_coherence_scores():
    tokenized_docs = _synthetic_tokenized_corpus()
    dictionary, _ = prepare_lda_matrices(tokenized_docs, use_tfidf=False)
    tfidf_matrix, vectorizer = prepare_nmf_matrix(tokenized_docs, dictionary)

    trainer = NMFTrainer(tfidf_matrix, vectorizer)
    trainer.train(num_topics=6)
    cv_score, umass_score = trainer.evaluate(tokenized_docs, dictionary)

    assert cv_score is not None
    assert umass_score is not None
    assert 0.0 <= cv_score <= 1.0
    assert umass_score <= 0.0  # u_mass is non-positive by definition


def test_nmf_trainer_evaluate_before_train_returns_none():
    tokenized_docs = _synthetic_tokenized_corpus()
    dictionary, _ = prepare_lda_matrices(tokenized_docs, use_tfidf=False)
    tfidf_matrix, vectorizer = prepare_nmf_matrix(tokenized_docs, dictionary)

    trainer = NMFTrainer(tfidf_matrix, vectorizer)
    cv_score, umass_score = trainer.evaluate(tokenized_docs, dictionary)

    assert cv_score is None and umass_score is None


def test_calculate_topic_diversity_range():
    topics = [["a", "b", "c"], ["c", "d", "e"], ["a", "f", "g"]]
    diversity = calculate_topic_diversity(topics)
    assert 0.0 < diversity <= 1.0


def test_calculate_topic_diversity_empty():
    assert calculate_topic_diversity([]) == 0.0


def test_run_nmf_grid_search_same_range_as_lda():
    tokenized_docs = _synthetic_tokenized_corpus()
    dictionary, _ = prepare_lda_matrices(tokenized_docs, use_tfidf=False)

    topic_range = [3, 6, 9]
    results_df = run_nmf_grid_search(tokenized_docs, dictionary, topic_range=topic_range)

    assert list(results_df["K"]) == topic_range
    assert "coherence" in results_df.columns
    assert "u_mass" in results_df.columns
    assert results_df["coherence"].notna().all()


def test_pick_best_from_grid_picks_highest_coherence():
    df = pd.DataFrame([
        {"K": 5, "coherence": 0.30, "u_mass": -2.0},
        {"K": 8, "coherence": 0.55, "u_mass": -1.5},
        {"K": 10, "coherence": 0.40, "u_mass": -1.8},
    ])
    best = _pick_best_from_grid(df)
    assert best["K"] == 8


def test_tokenize_corpus_uses_lang_api_field():
    df = pd.DataFrame([
        {"text": "the government election vote", "lang_api": "en"},
        {"text": "dowlad doorasho wasiir", "lang_api": "so"},
        {"text": "unspecified language text here", "lang_api": "und"},
    ])
    tokenized = _tokenize_corpus(df)
    assert len(tokenized) == 3
    assert all(isinstance(doc, list) for doc in tokenized)


def test_run_nmf_sync_end_to_end_on_dummy_data():
    """Full sandbox run of the synchronous NMF training step on synthetic data only."""
    tokenized_docs = _synthetic_tokenized_corpus()

    result = _run_nmf_sync(tokenized_docs, use_grid=True)

    assert result["num_topics"] in [5, 8, 10, 12]
    assert result["coherence"] is not None
    assert result["u_mass"] is not None
    assert 0.0 <= result["diversity"] <= 1.0
    assert len(result["grid_results"]) == 4  # topic_range = [5, 8, 10, 12]
