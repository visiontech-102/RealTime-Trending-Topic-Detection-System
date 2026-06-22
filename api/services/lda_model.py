import re
import os
import logging
from pathlib import Path
import nltk
import pandas as pd
import numpy as np
import scipy
import scipy.linalg

# Run compatibility patch: gensim expects triu in scipy.linalg, which was removed in scipy >= 1.13
if not hasattr(scipy.linalg, 'triu'):
    scipy.linalg.triu = np.triu

from gensim.corpora import Dictionary
from gensim.models import LdaModel, TfidfModel
from gensim.models.coherencemodel import CoherenceModel
import pyLDAvis
import pyLDAvis.gensim_models as gensimvis

logger = logging.getLogger(__name__)

# Download required NLTK components
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

# English Stopwords
english_stopwords = set(nltk.corpus.stopwords.words('english'))

# Somali stopwords — loaded from the single source of truth at api/resources/stopwords.txt.
# Path is resolved relative to this file so it works regardless of launch directory.
_SOMALI_STOPWORDS_PATH = Path(__file__).resolve().parent.parent / "resources" / "stopwords.txt"


def _load_somali_stopwords(path: Path) -> set:
    if not path.exists():
        logger.error(
            "Somali stopwords file NOT FOUND at %s — "
            "Somali preprocessing will have no stopword filtering. "
            "Restore the file and restart the server.",
            path,
        )
        return set()
    with path.open(encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip()}


somali_stopwords = _load_somali_stopwords(_SOMALI_STOPWORDS_PATH)

def preprocess_lda(text: str, lang: str) -> list:
    """
    Executes heavy sequential preprocessing for LDA:
    1. Lowercasing
    2. URL & Mention removal
    3. Stopword removal (English + Custom Somali)
    4. Tokenisation
    """
    if not isinstance(text, str):
        return []
    
    # 1. Lowercasing
    text = text.lower()
    
    # 2. URL and Mention Removal
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\@\w+', '', text)
    
    # Keep alphabetical/alphanumeric words only for tokenization
    text = re.sub(r'[^\w\s]', '', text)
    
    # 4. Tokenisation
    tokens = nltk.word_tokenize(text)
    
    # 3. Stopword Removal & Filtering tokens shorter than 3 letters
    if lang == 'en':
        cleaned = [w for w in tokens if w not in english_stopwords and len(w) > 2]
    elif lang == 'so':
        cleaned = [w for w in tokens if w not in somali_stopwords and len(w) > 2]
    else:
        # Fallback filter
        all_stopwords = english_stopwords.union(somali_stopwords)
        cleaned = [w for w in tokens if w not in all_stopwords and len(w) > 2]
        
    return cleaned

def prepare_lda_matrices(tokenized_docs: list, use_tfidf: bool = False):
    """
    Prepares Bag-of-Words and optionally TF-IDF matrices from preprocessed tokens.
    """
    dictionary = Dictionary(tokenized_docs)
    # Filter extremes to prevent noise
    dictionary.filter_extremes(no_below=2, no_above=0.95)
    
    corpus_bow = [dictionary.doc2bow(doc) for doc in tokenized_docs]
    
    if use_tfidf:
        tfidf = TfidfModel(corpus_bow)
        corpus_matrix = tfidf[corpus_bow]
        return dictionary, corpus_matrix
    
    return dictionary, corpus_bow

class LDATrainer:
    """
    Manages LDA training, hyperparameter tuning, evaluation, and pyLDAvis generation.
    """
    def __init__(self, dictionary, corpus):
        self.dictionary = dictionary
        self.corpus = corpus
        self.model = None

    def train(self, num_topics: int, alpha: str = 'symmetric', eta: str = 'symmetric', passes: int = 10):
        """
        Trains the Latent Dirichlet Allocation (LDA) model using gensim.
        """
        logger.info(f"Training LDA with K={num_topics}, alpha={alpha}, eta/beta={eta}")
        self.model = LdaModel(
            corpus=self.corpus,
            id2word=self.dictionary,
            num_topics=num_topics,
            alpha=alpha,
            eta=eta,
            passes=passes,
            random_state=42
        )
        return self.model

    def evaluate(self, tokenized_docs: list):
        """
        Evaluates LDA quality using:
        1. Coherence Score (Cv)
        2. Perplexity
        """
        if not self.model:
            logger.warning("No model trained yet for evaluation.")
            return None, None
            
        # Coherence Score (Cv)
        # processes=1: gensim's default multiprocessing pool deadlocks on
        # Windows when invoked without a `if __name__ == "__main__"` guard
        # (e.g. under pytest or uvicorn's reload subprocess).
        coherence_model = CoherenceModel(
            model=self.model,
            texts=tokenized_docs,
            dictionary=self.dictionary,
            coherence='c_v',
            processes=1
        )
        coherence_score = coherence_model.get_coherence()
        
        # Perplexity (lower indicates a better fit)
        perplexity = self.model.log_perplexity(self.corpus)
        
        return coherence_score, perplexity

    def generate_visualization(self, html_path: str):
        """
        Generates intertopic distance maps using pyLDAvis and saves it as HTML.
        """
        if not self.model:
            logger.warning("No model trained yet for visualization.")
            return
            
        vis_data = gensimvis.prepare(self.model, self.corpus, self.dictionary)
        pyLDAvis.save_html(vis_data, html_path)
        logger.info(f"pyLDAvis visualization saved successfully to {html_path}")

def run_lda_grid_search(tokenized_docs: list, corpus, dictionary, topic_range: list, alphas: list, betas: list):
    """
    Executes hyperparameter tuning via grid search to identify optimal K, alpha, and beta parameters.
    """
    results = []
    for k in topic_range:
        for alpha in alphas:
            for beta in betas:
                trainer = LDATrainer(dictionary, corpus)
                trainer.train(num_topics=k, alpha=alpha, eta=beta, passes=5)
                c_score, perp = trainer.evaluate(tokenized_docs)
                results.append({
                    'K': k,
                    'alpha': alpha,
                    'beta': beta,
                    'coherence': c_score,
                    'perplexity': perp
                })
    return pd.DataFrame(results)

def split_corpus_temporally(tweets: list, interval_hours: int = 24) -> dict:
    """
    Applies temporal splits to the collected tweet corpus for trend tracking,
    grouping tweets by custom time periods (e.g. 24 hours).
    """
    splits = {}
    for tweet in tweets:
        created_at = tweet.get('created_at')
        if not created_at:
            continue
        # Convert to datetime if it is a string
        if isinstance(created_at, str):
            dt = pd.to_datetime(created_at, utc=True)
        else:
            dt = pd.to_datetime(created_at)
            if dt.tzinfo is None:
                dt = dt.tz_localize('UTC')
            else:
                dt = dt.tz_convert('UTC')
            
        # Group by rounded timestamp based on interval hours
        rounded_ts = dt.floor(f'{interval_hours}h').isoformat()
        if rounded_ts not in splits:
            splits[rounded_ts] = []
        splits[rounded_ts].append(tweet)
    return splits

def get_document_topic_distribution(model, dictionary, tokenized_doc: list) -> list:
    """
    Returns the soft clustering probability distribution for a single document
    across all identified topics.
    """
    bow = dictionary.doc2bow(tokenized_doc)
    return model.get_document_topics(bow)

def get_topic_vocabulary_distribution(model, num_words: int = 10) -> dict:
    """
    Inspects generated topics and returns the probability distribution over vocabulary terms.
    """
    topics_dict = {}
    for topic_id in range(model.num_topics):
        # show_topic returns a list of tuples (word, probability)
        terms = model.show_topic(topic_id, topn=num_words)
        topics_dict[topic_id] = {word: float(prob) for word, prob in terms}
    return topics_dict

