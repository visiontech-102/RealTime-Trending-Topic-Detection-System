"""
Computes trend_score for detected topics from volume and engagement.
"""
from typing import Iterable


def compute_trend_score(
    doc_count: int,
    total_likes: int,
    total_retweets: int,
    corpus_max_engagement: int = 1,
) -> float:
    """
    Weighted score: document volume (60%) + normalized engagement (40%).

    corpus_max_engagement avoids division by zero; caller should pass
    max engagement seen in the current batch (at least 1).
    """
    if doc_count <= 0:
        return 0.0

    volume_component = min(doc_count / 100.0, 1.0) * 60.0
    engagement = total_likes + total_retweets
    engagement_component = min(engagement / max(corpus_max_engagement, 1), 1.0) * 40.0
    return round(volume_component + engagement_component, 4)


def dominant_language(langs: Iterable[str]) -> dict:
    """Calculate document counts for each language category in a topic."""
    counts = {"en": 0, "so": 0, "others": 0}
    for lang in langs:
        if lang == "en":
            counts["en"] += 1
        elif lang == "so":
            counts["so"] += 1
        else:
            counts["others"] += 1
    return counts
