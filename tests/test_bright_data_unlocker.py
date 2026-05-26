import httpx
import respx
import pytest
from wedge.bright_data import BrightDataClient


@pytest.mark.asyncio
async def test_unlocker_fetch_returns_html(fixtures_dir):
    html = (fixtures_dir / "reddit_asana_thread.html").read_text()
    async with respx.mock(base_url="https://api.brightdata.com") as mock:
        mock.post("/request").mock(return_value=httpx.Response(200, text=html))
        client = BrightDataClient()
        try:
            body = await client.fetch("https://reddit.com/r/x/comments/y")
            assert "Why we left Asana" in body
            assert client.call_count == 1
        finally:
            await client.aclose()
