"""
End-to-end tests for the Privacy & Security surface: 2FA enrolment, 2FA-gated
login, brute-force limits, and Google credential verification.
"""
import os
from datetime import datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app import routes
from services.auth import hash_2fa_code

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

USERNAME = "sec_user"
EMAIL = "sec_user@example.com"
PASSWORD = "Str0ngPassw0rd!"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def registered(client, test_db):
    resp = await client.post(
        "/auth/signup",
        json={"username": USERNAME, "email": EMAIL, "password": PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _login(client, password=PASSWORD):
    return await client.post(
        "/auth/login",
        data={"username": EMAIL, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


async def _enable_2fa_directly(test_db, code="123456"):
    """
    Put the account into an enrolled state with a known code, without email.

    `two_factor_code_sent_at` is set to now so the login step reuses this code
    instead of mailing a fresh one — that is the same resend-cooldown path a
    user hits when retrying login, and it keeps the seeded code predictable.
    """
    await test_db["users"].update_one(
        {"username": USERNAME},
        {"$set": {
            "two_factor_enabled": True,
            "two_factor_code_hash": hash_2fa_code(code),
            "two_factor_expires": datetime.utcnow() + timedelta(minutes=10),
            "two_factor_code_sent_at": datetime.utcnow(),
            "two_factor_attempts": 0,
        }},
    )


async def test_login_without_2fa_returns_token(client, registered):
    body = (await _login(client)).json()
    assert body["access_token"]
    assert body["requires_2fa"] is False


async def test_login_with_2fa_withholds_token(client, registered, test_db):
    await _enable_2fa_directly(test_db)
    body = (await _login(client)).json()

    assert body["requires_2fa"] is True
    assert body["access_token"] is None, "no session may be issued before the second factor"
    assert body["challenge_token"]


async def test_challenge_token_cannot_access_protected_routes(client, registered, test_db):
    await _enable_2fa_directly(test_db)
    challenge = (await _login(client)).json()["challenge_token"]

    resp = await client.get(
        "/auth/2fa/status",
        headers={"Authorization": f"Bearer {challenge}"},
    )
    assert resp.status_code == 401, "challenge token must not work as a session token"


async def test_correct_code_completes_login(client, registered, test_db):
    await _enable_2fa_directly(test_db, code="654321")
    challenge = (await _login(client)).json()["challenge_token"]

    resp = await client.post(
        "/auth/login/2fa",
        json={"challenge_token": challenge, "code": "654321"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]

    status_resp = await client.get(
        "/auth/2fa/status", headers={"Authorization": f"Bearer {token}"}
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["two_factor_enabled"] is True


async def test_code_is_single_use(client, registered, test_db):
    await _enable_2fa_directly(test_db, code="111222")
    challenge = (await _login(client)).json()["challenge_token"]

    first = await client.post(
        "/auth/login/2fa", json={"challenge_token": challenge, "code": "111222"}
    )
    assert first.status_code == 200

    replay = await client.post(
        "/auth/login/2fa", json={"challenge_token": challenge, "code": "111222"}
    )
    assert replay.status_code == 400, "a consumed code must not be replayable"


async def test_brute_force_is_capped(client, registered, test_db):
    await _enable_2fa_directly(test_db, code="999888")
    challenge = (await _login(client)).json()["challenge_token"]

    statuses = []
    for _ in range(routes.TWO_FA_MAX_ATTEMPTS + 1):
        r = await client.post(
            "/auth/login/2fa", json={"challenge_token": challenge, "code": "000000"}
        )
        statuses.append(r.status_code)

    assert 429 in statuses, f"expected lockout within {routes.TWO_FA_MAX_ATTEMPTS} attempts, got {statuses}"

    # The real code is burned along with the attempts budget.
    after = await client.post(
        "/auth/login/2fa", json={"challenge_token": challenge, "code": "999888"}
    )
    assert after.status_code in (400, 429)


async def test_expired_code_is_rejected(client, registered, test_db):
    await _enable_2fa_directly(test_db, code="777666")
    challenge = (await _login(client)).json()["challenge_token"]

    await test_db["users"].update_one(
        {"username": USERNAME},
        {"$set": {"two_factor_expires": datetime.utcnow() - timedelta(seconds=1)}},
    )

    resp = await client.post(
        "/auth/login/2fa", json={"challenge_token": challenge, "code": "777666"}
    )
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"].lower()


async def test_plaintext_code_is_never_stored(client, registered, test_db):
    await client.post(
        "/auth/login/2fa", json={"challenge_token": "bogus", "code": "000000"}
    )
    await _enable_2fa_directly(test_db, code="424242")
    await _login(client)

    user = await test_db["users"].find_one({"username": USERNAME})
    assert "two_factor_code" not in user, "plaintext code column must be gone"
    assert user["two_factor_code_hash"] != "424242"
    assert user["two_factor_code_hash"].startswith("$2")


async def test_disable_2fa_requires_reauthentication(client, registered, test_db):
    """A stolen session token alone must not be enough to strip the second factor."""
    await _enable_2fa_directly(test_db, code="313131")
    challenge = (await _login(client)).json()["challenge_token"]
    token = (await client.post(
        "/auth/login/2fa", json={"challenge_token": challenge, "code": "313131"}
    )).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    no_proof = await client.post("/auth/2fa/disable", json={}, headers=auth)
    assert no_proof.status_code == 400

    wrong = await client.post(
        "/auth/2fa/disable", json={"password": "not-the-password"}, headers=auth
    )
    assert wrong.status_code == 400

    still_on = await client.get("/auth/2fa/status", headers=auth)
    assert still_on.json()["two_factor_enabled"] is True

    correct = await client.post(
        "/auth/2fa/disable", json={"password": PASSWORD}, headers=auth
    )
    assert correct.status_code == 200

    now_off = await client.get("/auth/2fa/status", headers=auth)
    assert now_off.json()["two_factor_enabled"] is False


async def test_disable_2fa_accepts_emailed_code(client, registered, test_db):
    """Google-provisioned accounts have no known password, so a code must work."""
    await _enable_2fa_directly(test_db, code="565656")
    challenge = (await _login(client)).json()["challenge_token"]
    token = (await client.post(
        "/auth/login/2fa", json={"challenge_token": challenge, "code": "565656"}
    )).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    # Logging in consumed that code; seed a fresh one the way send-code would.
    await _enable_2fa_directly(test_db, code="787878")

    wrong = await client.post("/auth/2fa/disable", json={"code": "000000"}, headers=auth)
    assert wrong.status_code == 400

    ok = await client.post("/auth/2fa/disable", json={"code": "787878"}, headers=auth)
    assert ok.status_code == 200

    status_resp = await client.get("/auth/2fa/status", headers=auth)
    assert status_resp.json()["two_factor_enabled"] is False


@pytest.mark.parametrize("weak", ["short1", "nodigitshere", "12345678"])
async def test_signup_rejects_weak_passwords(client, test_db, weak):
    resp = await client.post(
        "/auth/signup",
        json={"username": "weak_user", "email": "weak@example.com", "password": weak},
    )
    assert resp.status_code == 422, f"{weak!r} should be rejected"


async def test_change_password_enforces_policy_and_difference(client, registered, test_db):
    token = (await _login(client)).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    weak = await client.post(
        "/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "abc"},
        headers=auth,
    )
    assert weak.status_code == 422

    same = await client.post(
        "/auth/change-password",
        json={"current_password": PASSWORD, "new_password": PASSWORD},
        headers=auth,
    )
    assert same.status_code == 400

    ok = await client.post(
        "/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "An0therGoodPass"},
        headers=auth,
    )
    assert ok.status_code == 200


async def test_forged_google_credential_is_rejected(client, test_db):
    """An unsigned JWT with an arbitrary email must not mint a session."""
    from jose import jwt as jose_jwt

    forged = jose_jwt.encode(
        {"email": "victim@example.com", "email_verified": True},
        "attacker-key",
        algorithm="HS256",
    )
    resp = await client.post("/auth/google", json={"credential": forged})

    assert resp.status_code in (401, 503), resp.text
    assert "access_token" not in resp.text or resp.json().get("access_token") is None
