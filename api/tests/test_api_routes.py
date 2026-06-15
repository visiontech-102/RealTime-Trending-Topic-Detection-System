"""HTTP route smoke tests (no MongoDB — sync endpoints only)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "message" in r.json()


def test_visualization_404_when_not_generated():
    r = client.get("/visualizations/lda")
    assert r.status_code == 404
