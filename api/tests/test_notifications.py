from services.notifications import _detect_spikes


def test_detect_spikes_pct_increase():
    previous = [{"Name": "Politics", "trend_score": 40.0}]
    current = [{"Name": "Politics", "trend_score": 55.0, "Representation": ["vote"]}]
    spikes = _detect_spikes(current, previous)
    assert len(spikes) == 1
    assert spikes[0]["topic_name"] == "Politics"
    assert spikes[0]["pct_change"] == 37.5


def test_detect_spikes_no_change():
    previous = [{"Name": "Economy", "trend_score": 50.0}]
    current = [{"Name": "Economy", "trend_score": 52.0}]
    spikes = _detect_spikes(current, previous)
    assert len(spikes) == 0


def test_detect_spikes_new_high_score_topic():
    previous = []
    current = [{"Name": "NewTopic", "trend_score": 60.0, "Representation": []}]
    spikes = _detect_spikes(current, previous)
    assert len(spikes) == 1
