"""Email service tests (SMTP optional)."""
from unittest.mock import patch, MagicMock

import pytest

from services import email as email_svc


@pytest.mark.asyncio
async def test_console_mode_when_smtp_disabled():
    with patch.object(email_svc, "SMTP_ENABLED", False):
        ok = await email_svc._send_email("user@test.com", "Test", "Body")
    assert ok is True


@pytest.mark.asyncio
async def test_smtp_send_when_enabled():
    with patch.object(email_svc, "SMTP_ENABLED", True), \
         patch.object(email_svc, "SMTP_HOST", "smtp.test.com"), \
         patch.object(email_svc, "_send_smtp_sync") as mock_smtp:
        ok = await email_svc._send_email("user@test.com", "Subject", "Body")
    assert ok is True
    mock_smtp.assert_called_once_with("user@test.com", "Subject", "Body")


def test_smtp_configured_requires_host():
    with patch.object(email_svc, "SMTP_ENABLED", True), \
         patch.object(email_svc, "SMTP_HOST", ""):
        assert email_svc._smtp_configured() is False
    with patch.object(email_svc, "SMTP_ENABLED", True), \
         patch.object(email_svc, "SMTP_HOST", "smtp.example.com"):
        assert email_svc._smtp_configured() is True
