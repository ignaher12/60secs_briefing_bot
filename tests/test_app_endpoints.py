import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("WEDGE_DB_PATH", ":memory:")
    monkeypatch.setenv("NVIDIA_API_KEY", "test")
    monkeypatch.setenv("BRIGHT_DATA_API_TOKEN", "test")
    monkeypatch.setenv("BRIGHT_DATA_SERP_ZONE", "test")
    monkeypatch.setenv("BRIGHT_DATA_UNLOCKER_ZONE", "test")
    monkeypatch.setenv("BRIGHT_DATA_BROWSER_WS", "ws://test")
    import wedge.app as app_mod
    app_mod._db = None  # force re-init
    return TestClient(app_mod.app)


def test_index_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "idea" in r.text.lower()


def test_generate_creates_job(client):
    r = client.post("/generate", data={"idea": "AI notes for sales"})
    assert r.status_code in (200, 303)
    assert "progress" in r.text.lower() or "/progress/" in r.headers.get("location", "")
