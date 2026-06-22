import logging

import pandas as pd
from gensim.models.coherencemodel import CoherenceModel
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)


def prepare_nmf_matrix(tokenized_docs: list, dictionary):
    """
    Builds a TF-IDF matrix restricted to the SAME vocabulary as the shared
    gensim Dictionary used by LDA (same no_below/no_above filtering), so LDA
    and NMF factorize an identical vocabulary — only the weighting scheme
    (BoW vs TF-IDF) and the decomposition technique differ.
    """
    vectorizer = TfidfVectorizer(
        vocabulary=dictionary.token2id,
        analyzer=lambda tokens: tokens,
        lowercase=False,
    )
    tfidf_matrix = vectorizer.fit_transform(tokenized_docs)
    return tfidf_matrix, vectorizer


class NMFTrainer:
    """
    Manages NMF training and evaluation on the shared TF-IDF representation.
    """

    def __init__(self, tfidf_matrix, vectorizer):
        self.tfidf_matrix = tfidf_matrix
        self.vectorizer = vectorizer
        self.feature_names = vectorizer.get_feature_names_out()
        self.model = None

    def train(self, num_topics: int):
        """
        Trains an NMF model via scikit-learn. K must be set in advance,
        same as LDA (selected by grid search elsewhere).
        """
        logger.info(f"Training NMF with K={num_topics}")
        self.model = NMF(
            n_components=num_topics,
            init="nndsvda",
            max_iter=400,
            random_state=42,
        )
        self.model.fit(self.tfidf_matrix)
        return self.model

    def get_topics(self, num_words: int = 10) -> list:
        """Returns a list of top-word lists, one per topic (for coherence scoring)."""
        if self.model is None:
            return []
        topics = []
        for component in self.model.components_:
            top_indices = component.argsort()[::-1][:num_words]
            topics.append([self.feature_names[i] for i in top_indices])
        return topics

    def evaluate(self, tokenized_docs: list, dictionary, num_words: int = 10):
        """
        Evaluates NMF quality using:
        1. C_v Coherence (primary)
        2. U_Mass Coherence (supporting)
        NMF is non-probabilistic, so no perplexity is computed here by design.
        """
        if self.model is None:
            logger.warning("No model trained yet for evaluation.")
            return None, None

        topics = self.get_topics(num_words=num_words)

        # processes=1: gensim's default multiprocessing pool deadlocks on
        # Windows when invoked without a `if __name__ == "__main__"` guard
        # (e.g. under pytest or uvicorn's reload subprocess).
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

    def get_topic_vocabulary_distribution(self, num_words: int = 10) -> dict:
        """Mirrors LDA's get_topic_vocabulary_distribution for consistent reporting."""
        if self.model is None:
            return {}
        topics_dict = {}
        for topic_id, component in enumerate(self.model.components_):
            top_indices = component.argsort()[::-1][:num_words]
            topics_dict[topic_id] = {
                self.feature_names[i]: float(component[i]) for i in top_indices
            }
        return topics_dict


def calculate_topic_diversity(topics: list) -> float:
    """
    Topic Diversity: proportion of unique words across the top-N words of all
    topics. Same definition used for BERTopic, generalised to a plain
    list-of-word-lists so LDA/NMF/BERTopic diversity scores are comparable.
    """
    all_words = [w for topic in topics for w in topic]
    if not all_words:
        return 0.0
    return len(set(all_words)) / len(all_words)


def run_nmf_grid_search(tokenized_docs: list, dictionary, topic_range: list, num_words: int = 10):
    """
    Hyperparameter search over K using the SAME candidate range and SAME
    selection criterion (highest C_v coherence) as run_lda_grid_search.
    """
    tfidf_matrix, vectorizer = prepare_nmf_matrix(tokenized_docs, dictionary)
    results = []
    for k in topic_range:
        trainer = NMFTrainer(tfidf_matrix, vectorizer)
        trainer.train(num_topics=k)
        cv_score, umass_score = trainer.evaluate(tokenized_docs, dictionary, num_words=num_words)
        results.append({
            "K": k,
            "coherence": cv_score,
            "u_mass": umass_score,
        })
    return pd.DataFrame(results)
