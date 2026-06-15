from services.trend_scoring import compute_trend_score, dominant_language


def test_compute_trend_score_volume_only():
    score = compute_trend_score(doc_count=50, total_likes=0, total_retweets=0, corpus_max_engagement=100)
    assert 0 < score <= 60


def test_compute_trend_score_with_engagement():
    score = compute_trend_score(doc_count=10, total_likes=80, total_retweets=20, corpus_max_engagement=100)
    assert score > compute_trend_score(10, 0, 0, 100)


def test_compute_trend_score_zero_docs():
    assert compute_trend_score(0, 10, 10, 100) == 0.0


def test_dominant_language_english():
    assert dominant_language(["en", "en", "en", "so"]) == {"en": 3, "so": 1, "others": 0}


def test_dominant_language_mixed():
    assert dominant_language(["en", "so", "en", "so"]) == {"en": 2, "so": 2, "others": 0}


def test_dominant_language_somali():
    assert dominant_language(["so", "so", "so"]) == {"en": 0, "so": 3, "others": 0}
