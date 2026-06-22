"""
Computes trend_score for detected topics from volume and engagement.
"""
from typing import Iterable

_NOISE_BLOCKLIST = frozenset({'https', 'http', 'www', 'co', 'rt', 'amp', 't'})


def _is_hash_like(token: str) -> bool:
    """True for URL-fragment / handle tokens: all-alphanumeric, length >= 5, mixed letters+digits."""
    return (
        token.isalnum()
        and len(token) >= 5
        and any(c.isdigit() for c in token)
        and any(c.isalpha() for c in token)
    )


def clean_keywords(words: list) -> list:
    """Remove URL noise tokens and hash-like fragments from a topic keyword list."""
    return [w for w in words if w.lower() not in _NOISE_BLOCKLIST and not _is_hash_like(w)]


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


def generate_topic_label(keywords: list, n: int = 3) -> str:
    cleaned = clean_keywords(keywords) if keywords else []
    if not cleaned:
        return "Unknown Topic"
    words = [w.replace("_", " ").title() for w in cleaned[:n]]
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " & " + words[-1]
