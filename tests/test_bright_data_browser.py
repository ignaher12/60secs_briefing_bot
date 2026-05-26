import pytest
from wedge.bright_data import BrightDataClient

class FakePage:
    async def goto(self, url, timeout=None): self.url = url
    async def content(self): return f"<html>fake content for {self.url}</html>"
    async def close(self): pass

class FakeContext:
    async def new_page(self): return FakePage()
    async def close(self): pass

class FakeBrowser:
    async def new_context(self): return FakeContext()
    async def close(self): pass

class FakePlaywright:
    async def __aenter__(self): return self
    async def __aexit__(self, *a): pass
    class chromium:
        @staticmethod
        async def connect_over_cdp(ws): return FakeBrowser()

@pytest.mark.asyncio
async def test_browser_render_returns_content(monkeypatch):
    client = BrightDataClient()
    monkeypatch.setattr(client, "_playwright_factory", lambda: FakePlaywright())
    html = await client.browser_render("https://g2.com/p/asana")
    assert "fake content for https://g2.com/p/asana" in html
    assert client.call_count == 1
