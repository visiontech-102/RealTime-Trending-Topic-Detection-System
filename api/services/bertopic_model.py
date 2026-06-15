import os
import logging
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
from umap import UMAP
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from services.lda_model import english_stopwords, somali_stopwords

logger = logging.getLogger(__name__)

def preprocess_bertopic(df: pd.DataFrame, text_col: str = 'text') -> pd.DataFrame:
    """
    Executes minimal preprocessing for BERTopic:
    Preserves original sentence structure and word order (does not apply stemming or lemmatisation).
    Performs basic noise removal (e.g. removing exact duplicates).
    """
    logger.info("Executing minimal preprocessing for BERTopic...")
    if df.empty or text_col not in df.columns:
        return df
    
    # 1. Remove duplicate tweets
    df_clean = df.drop_duplicates(subset=[text_col]).copy()
    
    # Minimal cleaning (retaining full sentence context and punctuation)
    # Just trim whitespace
    df_clean['clean_text'] = df_clean[text_col].astype(str).str.strip()
    
    # Remove empty tweets
    df_clean = df_clean[df_clean['clean_text'] != '']
    return df_clean

class BERTopicTrainer:
    """
    Manages the 4-stage modular BERTopic pipeline:
    1. Embeddings (SentenceTransformer MiniLM-L12-v2)
    2. Dimensionality Reduction (UMAP)
    3. Clustering (HDBSCAN)
    4. Topic Representation (c-TF-IDF)
    """
    def __init__(self, embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", min_cluster_size: int = 10, n_neighbors: int = 15):
        logger.info(f"Initializing BERTopic pipeline with embedding model: {embedding_model_name}")
        self.embedding_model = SentenceTransformer(embedding_model_name)
        
        # UMAP Dimensionality Reduction
        self.umap_model = UMAP(n_neighbors=n_neighbors, n_components=5, min_dist=0.0, metric='cosine', random_state=42)
        
        # HDBSCAN Clustering
        self.hdbscan_model = HDBSCAN(min_cluster_size=min_cluster_size, metric='euclidean', cluster_selection_method='eom', prediction_data=True)
        
        # Count Vectorizer for c-TF-IDF representation (filtering custom English + Somali stopwords)
        combined_stopwords = list(english_stopwords.union(somali_stopwords))
        self.vectorizer_model = CountVectorizer(stop_words=combined_stopwords)
        
        # Initialize BERTopic model architecture
        self.topic_model = BERTopic(
            embedding_model=self.embedding_model,
            umap_model=self.umap_model,
            hdbscan_model=self.hdbscan_model,
            vectorizer_model=self.vectorizer_model,
            nr_topics="None", 
            calculate_probabilities=True
        )
        self.is_fitted = False
        self._training_docs: list = []

    def train(self, docs: list):
        """
        Executes independent Model Training sequentially:
        Embedding extraction -> UMAP reduction -> HDBSCAN clustering -> c-TF-IDF representation.
        """
        logger.info(f"Training BERTopic on {len(docs)} documents...")
        if not docs:
            return [], []
            
        # 1. Generate Contextual Vector Embeddings in a single unified semantic vector space
        embeddings = self.embedding_model.encode(docs, show_progress_bar=False)
        
        # Fit and transform
        topics, probabilities = self.topic_model.fit_transform(docs, embeddings)
        if probabilities is None:
            probabilities = []
        self.is_fitted = True
        self._training_docs = list(docs)
        return topics, probabilities

    def evaluate_cohesion(self, docs: list, topics: list) -> float:
        """
        Evaluates topic cohesion using Cosine Similarity between document embeddings within topics.
        """
        if not self.is_fitted or not docs:
            return 0.0
            
        unique_topics = set(topics)
        if -1 in unique_topics:
            unique_topics.remove(-1)

        if not unique_topics:
            return 0.0

        embeddings = self.embedding_model.encode(docs, show_progress_bar=False)
        cohesion_scores = []
        for topic in unique_topics:
            indices = [i for i, t in enumerate(topics) if t == topic]
            if len(indices) < 2:
                continue
            topic_embeddings = embeddings[indices]
            
            # Compute mean pairwise cosine similarity inside the topic
            sim_matrix = cosine_similarity(topic_embeddings)
            # Take upper triangle indices to avoid self-similarity diagonal
            upper_tri_indices = np.triu_indices(sim_matrix.shape[0], k=1)
            if len(upper_tri_indices[0]) > 0:
                mean_sim = np.mean(sim_matrix[upper_tri_indices])
                cohesion_scores.append(mean_sim)
                
        return np.mean(cohesion_scores) if cohesion_scores else 0.0

    def run_dynamic_topic_modeling(self, docs: list, timestamps: list):
        """
        Activates Dynamic Topic Modeling to observe how topics evolve, peak, and decay over time
        based on time-series metadata.
        """
        if not self.is_fitted:
            logger.warning("BERTopic model must be trained before running Dynamic Topic Modeling.")
            return None
            
        logger.info("Running Dynamic Topic Modeling (time-series)...")
        # Format timestamps into appropriate string formats for DTM
        formatted_timestamps = [pd.to_datetime(ts).isoformat() for ts in timestamps]
        
        # compute topics over time
        topics_over_time = self.topic_model.topics_over_time(
            docs=docs,
            timestamps=formatted_timestamps,
            topics=self.topic_model.topics_
        )
        return topics_over_time

    def apply_hierarchical_reduction(self, num_topics: int):
        """
        Applies hierarchical topic reduction to dynamically merge low-volume topics and split high-volume ones.
        """
        if not self.is_fitted:
            logger.warning("BERTopic must be fitted before applying hierarchical reduction.")
            return
            
        docs = self._training_docs
        if not docs:
            logger.warning("No documents available for hierarchical reduction.")
            return
        logger.info(f"Reducing topics hierarchically to: {num_topics}")
        self.topic_model.reduce_topics(docs, nr_topics=num_topics)

    def generate_visualization(self, html_path: str):
        """
        Generates interactive visualizations of intertopic distances and boundaries in embedding space.
        """
        if not self.is_fitted:
            logger.warning("BERTopic must be fitted before generating visualisations.")
            return
            
        report_dir = os.path.dirname(html_path)
        if report_dir and not os.path.exists(report_dir):
            os.makedirs(report_dir, exist_ok=True)
            
        fig = self.topic_model.visualize_topics()
        fig.write_html(html_path)
        logger.info(f"BERTopic interactive visualization saved to {html_path}")

    def calculate_topic_diversity(self, top_n_words: int = 10) -> float:
        """
        Calculates Topic Diversity: the proportion of unique words across the top N words of all topics.
        """
        if not self.is_fitted:
            return 0.0
        
        # Get list of unique topic IDs (excluding -1 outlier)
        topics = list(self.topic_model.get_topics().keys())
        if -1 in topics:
            topics.remove(-1)
            
        if not topics:
            return 0.0
            
        all_words = []
        for topic in topics:
            words = [word for word, _ in self.topic_model.get_topic(topic)[:top_n_words]]
            all_words.extend(words)
            
        if not all_words:
            return 0.0
            
        unique_words = set(all_words)
        return len(unique_words) / len(all_words)

    def get_topic_statistics(self, topics: list) -> pd.DataFrame:
        """
        Calculates statistics for each topic including document count and corpus percentage.
        """
        if not topics:
            return pd.DataFrame()
            
        df_topics = pd.Series(topics).value_counts().reset_index()
        df_topics.columns = ['Topic', 'Count']
        df_topics['Percentage'] = (df_topics['Count'] / len(topics)) * 100
        
        # Map Topic Names if fitted
        if self.is_fitted:
            topic_names = self.topic_model.get_topic_info()[['Topic', 'Name']]
            df_topics = df_topics.merge(topic_names, on='Topic', how='left')
            
        return df_topics

        
    def generate_evaluation_report(self, docs: list, topics: list, report_path: str):

        """
        Generates and saves a detailed Evaluation Report including Cohesion, Diversity, and Topic Stats.
        """    

        if not self.is_fitted:
            logger.warning("Cannot generate report for unfitted model.")
            return

        if len(docs) != len(topics):
            logger.error("docs and topics must have equal length for report generation.")
            return

        cohesion = self.evaluate_cohesion(docs, topics)
        diversity = self.calculate_topic_diversity(top_n_words=10)
        stats = self.get_topic_statistics(topics)
        
        report_dir = os.path.dirname(report_path)
        if report_dir and not os.path.exists(report_dir):
            os.makedirs(report_dir, exist_ok=True)
            
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("==================================================\n")
            f.write("           BERTOPIC EVALUATION REPORT             \n")
            f.write("==================================================\n\n")
            f.write(f"Generated at: {pd.Timestamp.now().isoformat()}\n")
            f.write(f"Total Documents: {len(docs)}\n")
            f.write(f"Number of Topics (excl. outliers): {len(set(topics) - {-1})}\n\n")
            f.write("--------------------------------------------------\n")
            f.write("Metrics:\n")
            f.write(f" - Semantic Cohesion (Mean Cosine Similarity): {cohesion:.4f}\n")
            f.write(f" - Topic Diversity (Unique Keywords Ratio):  {diversity:.4f}\n")
            f.write("--------------------------------------------------\n\n")
            f.write("Topic Size Statistics:\n")
            f.write(stats.to_string(index=False))
            f.write("\n\n==================================================\n")
            
        logger.info(f"Evaluation report generated successfully at {report_path}")

    def inspect_topics(self, num_words: int = 10) -> dict:
        """
        Topic Inspection utility returning keywords and c-TF-IDF weights for all topics.
        """
        if not self.is_fitted:
            return {}
            
        topics = self.topic_model.get_topics()
        inspected = {}
        for topic_id, terms in topics.items():
            inspected[topic_id] = {word: float(score) for word, score in terms[:num_words]}
        return inspected

    def generate_research_report(self, config: dict, report_path: str):
        """
        Generates structured Research Report outputs to assist academic reporting in the thesis.
        """
        report_dir = os.path.dirname(report_path)
        if report_dir and not os.path.exists(report_dir):
            os.makedirs(report_dir, exist_ok=True)
            
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("==================================================\n")
            f.write("            FYP RESEARCH CONFIG REPORT            \n")
            f.write("==================================================\n\n")
            f.write(f"Project Name: Real-Time Trending Topic Detection System\n")
            f.write(f"Model Under Test: BERTopic (Transformer-based)\n")
            f.write(f"Date generated: {pd.Timestamp.now().isoformat()}\n\n")
            f.write("--------------------------------------------------\n")
            f.write("Model Configurations:\n")
            for k, v in config.items():
                f.write(f" - {k}: {v}\n")
            f.write("--------------------------------------------------\n")
            f.write("\nDocument note\n")
            f.write("==================================================\n")
            
        logger.info(f"Research configuration report saved to {report_path}")

