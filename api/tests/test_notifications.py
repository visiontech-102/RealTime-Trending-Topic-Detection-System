from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from services import notifications
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


# ---------------------------------------------------------------------------
# Delivery behaviour: that the preference Settings displays is the preference
# the sender honours, that restarts do not resend, and that reported counts
# reflect real deliveries.
# ---------------------------------------------------------------------------

delivery_tests = [pytest.mark.asyncio, pytest.mark.integration]


async def _seed_trends(test_db):
    batch_time = datetime.utcnow()
    await test_db["detected_trends"].insert_many([
        {"Name": "0_ai_tech", "Representation": ["ai", "tech"], "trend_score": 90.0,
         "calculated_at": batch_time},
        {"Name": "1_somalia", "Representation": ["somalia"], "trend_score": 70.0,
         "calculated_at": batch_time},
    ])


@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_who_never_opened_settings_still_receives_digest(test_db):
    """Settings reports digests as on by default, so the sender must agree."""
    await _seed_trends(test_db)
    await test_db["users"].insert_one({"username": "untouched", "email": "untouched@example.com"})

    with patch.object(notifications, "send_email_digest", AsyncMock(return_value=True)) as send:
        result = await notifications.send_daily_digests(force=True)

    assert result["recipients"] == 1, "a user with no preference field must still be included"
    assert result["digests_sent"] == 1
    send.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_opted_out_user_is_excluded(test_db):
    await _seed_trends(test_db)
    await test_db["users"].insert_many([
        {"username": "in", "email": "in@example.com", "email_digests": True},
        {"username": "out", "email": "out@example.com", "email_digests": False},
    ])

    with patch.object(notifications, "send_email_digest", AsyncMock(return_value=True)):
        result = await notifications.send_daily_digests(force=True)

    assert result["recipients"] == 1
    assert result["digests_sent"] == 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_restart_within_interval_does_not_resend(test_db):
    await _seed_trends(test_db)
    await test_db["users"].insert_one({"username": "u", "email": "u@example.com"})
    await test_db["pipeline_state"].insert_one({
        "pipeline": "notifications",
        "last_digest_at": datetime.now(timezone.utc) - timedelta(hours=1),
    })

    with patch.object(notifications, "send_email_digest", AsyncMock(return_value=True)) as send:
        result = await notifications.send_daily_digests()

    assert result["status"] == "skipped"
    assert result["reason"] == "interval_not_elapsed"
    send.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_send_resumes_once_interval_elapsed(test_db):
    await _seed_trends(test_db)
    await test_db["users"].insert_one({"username": "u", "email": "u@example.com"})
    await test_db["pipeline_state"].insert_one({
        "pipeline": "notifications",
        "last_digest_at": datetime.now(timezone.utc) - timedelta(hours=48),
    })

    with patch.object(notifications, "send_email_digest", AsyncMock(return_value=True)):
        result = await notifications.send_daily_digests()

    assert result["status"] == "ok"
    assert result["digests_sent"] == 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_manual_trigger_overrides_the_interval(test_db):
    await _seed_trends(test_db)
    await test_db["users"].insert_one({"username": "u", "email": "u@example.com"})
    await test_db["pipeline_state"].insert_one({
        "pipeline": "notifications",
        "last_digest_at": datetime.now(timezone.utc),
    })

    with patch.object(notifications, "send_email_digest", AsyncMock(return_value=True)):
        result = await notifications.send_daily_digests(force=True)

    assert result["status"] == "ok"
    assert result["digests_sent"] == 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_failed_delivery_is_not_counted_as_sent(test_db):
    """`digests_sent` must count deliveries, not attempts."""
    await _seed_trends(test_db)
    await test_db["users"].insert_many([
        {"username": "a", "email": "a@example.com"},
        {"username": "b", "email": "b@example.com"},
    ])

    # One recipient succeeds, the other is rejected by the mail server.
    with patch.object(notifications, "send_email_digest", AsyncMock(side_effect=[True, False])):
        result = await notifications.send_daily_digests(force=True)

    assert result["recipients"] == 2
    assert result["digests_sent"] == 1
    assert result["digests_failed"] == 1

    state = await test_db["pipeline_state"].find_one({"pipeline": "notifications"})
    assert state["digests_sent"] == 1
    assert state["digests_failed"] == 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_spike_alerts_only_go_to_opted_in_users(test_db):
    old_batch = datetime.utcnow() - timedelta(hours=1)
    new_batch = datetime.utcnow()
    await test_db["detected_trends"].insert_many([
        {"Name": "0_ai_tech", "Representation": ["ai"], "trend_score": 40.0, "calculated_at": old_batch},
        {"Name": "0_ai_tech", "Representation": ["ai"], "trend_score": 90.0, "calculated_at": new_batch},
    ])
    await test_db["users"].insert_many([
        {"username": "on", "email": "on@example.com", "spike_alerts": True},
        {"username": "off", "email": "off@example.com", "spike_alerts": False},
        {"username": "default", "email": "default@example.com"},  # spike alerts default to off
    ])

    with patch.object(notifications, "send_spike_alert", AsyncMock(return_value=True)):
        result = await notifications.check_and_send_spike_alerts()

    assert result["spikes_detected"] >= 1
    assert result["recipients"] == 1, "only the explicitly opted-in user should be alerted"
    assert result["alerts_sent"] == 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_signup_records_default_preferences(test_db):
    """The stored document must match what Settings will display."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/auth/signup", json={
            "username": "prefs_user",
            "email": "prefs_user@example.com",
            "password": "Str0ngPassw0rd!",
        })
    assert resp.status_code == 200, resp.text

    user = await test_db["users"].find_one({"username": "prefs_user"})
    assert user["email_digests"] is True
    assert user["spike_alerts"] is False
