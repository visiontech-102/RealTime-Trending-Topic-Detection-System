import asyncio
from datetime import datetime
import re
from bertopic import BERTopic
from database.connection import get_database

class AIEngine:
    def __init__(self):
        print("Initializing BERTopic model: paraphrase-multilingual-MiniLM-L12-v2")
        self.model = BERTopic(language="multilingual", embedding_model="paraphrase-multilingual-MiniLM-L12-v2")
        
    def preprocess_text(self, text: str) -> str:
        """Clean tweet text by removing URLs, mentions, hashtags, emojis, and extra whitespace."""
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        # Remove mentions (@username)
        text = re.sub(r'@\w+', '', text)
        # Remove hashtags (#hashtag) but keep the text
        text = re.sub(r'#\w+', '', text)
        # Remove emojis (basic pattern)
        text = re.sub(r'[^\w\s]', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
        
    async def process_batch(self, lang: str):
        db = await get_database()
        tweets_collection = db["raw_tweets"]
        trends_collection = db["trending_topics"]
        
        # Fetch recent tweets for this language
        cursor = tweets_collection.find({"language": lang}).sort("timestamp", -1).limit(200)
        tweets = await cursor.to_list(length=200)
        
        if len(tweets) < 10:
            print(f"[{lang}] Not enough tweets to form clusters.")
            return

        # Preprocess texts
        docs = [self.preprocess_text(t["text"]) for t in tweets]
        metrics = [t.get("engagement_metrics", 0) for t in tweets]
        
        try:
            # Fit BERTopic
            topics, probs = self.model.fit_transform(docs)
            
            # Extract info
            topic_info = self.model.get_topic_info()
            for index, row in topic_info.iterrows():
                topic_id = row['Topic']
                if topic_id == -1:
                    continue # Outlier topic
                
                # Get representative words
                keywords = [word for word, score in self.model.get_topic(topic_id)[:5]]
                topic_name = "_".join(keywords[:2])
                count = row['Count']
                
                # Calculate simple trend score (volume + engagement ratio)
                # For realism, we will find docs associated with this topic
                associated_tweets = [t for i, t in enumerate(tweets) if topics[i] == topic_id]
                avg_engagement = sum([t.get("engagement_metrics", 0) for t in associated_tweets]) / len(associated_tweets)
                velocity_score = count * 1.5 + avg_engagement * 0.5
                
                representative_docs = [t["text"] for t in associated_tweets[:3]]
                
                trend_doc = {
                    "topic_name": topic_name,
                    "top_keywords": keywords,
                    "representative_docs": representative_docs,
                    "score": velocity_score,
                    "language": lang,
                    "timestamp": datetime.utcnow()
                }
                
                # We could replace or insert. For history, we insert.
                await trends_collection.insert_one(trend_doc)
            print(f"[{lang}] Processed '{len(tweets)}' tweets. Discovered '{len(topic_info) - 1}' topics.")
                
        except Exception as e:
            print(f"[{lang}] BERTopic processing error: {e}")

async def run_ai_loop():
    """Background loop to periodically trigger the AI clustering."""
    engine = AIEngine()
    while True:
        await asyncio.sleep(60) # Run every 60 seconds
        print("Running AI topic detection loop...")
        await engine.process_batch("en")
        await engine.process_batch("so")
