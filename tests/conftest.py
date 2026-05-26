import os
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures"

@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic")
    monkeypatch.setenv("BRIGHT_DATA_API_TOKEN", "test-bd")
    monkeypatch.setenv("BRIGHT_DATA_SERP_ZONE", "serp_test")
    monkeypatch.setenv("BRIGHT_DATA_UNLOCKER_ZONE", "unlocker_test")
    monkeypatch.setenv("BRIGHT_DATA_BROWSER_WS", "wss://test")
    monkeypatch.setenv("WEDGE_DB_PATH", ":memory:")
    monkeypatch.setenv("WEDGE_BRIGHT_DATA_CALL_CAP", "40")

@pytest.fixture
def fixtures_dir():
    return FIXTURES
