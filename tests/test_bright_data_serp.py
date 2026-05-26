import json
import httpx
import respx
import pytest
from wedge.bright_data import BrightDataClient

@pytest.mark.asyncio
async def test_serp_search_returns_results(fixtures_dir):
    payload = json.loads((fixtures_dir / "serp_pm_tool.json").read_text())
    async with respx.mock(base_url="https://api.brightdata.com") as mock:
        mock.post("/request").mock(return_value=httpx.Response(200, json=payload))
        client = BrightDataClient()
        try:
            results = await client.serp_search("best project management tool")
            assert len(results) == 3
            assert results[0]["title"].startswith("Asana vs Trello")
            assert client.call_count == 1
        finally:
            await client.aclose()

@pytest.mark.asyncio
async def test_cap_exceeded_raises():
    from wedge.bright_data import BrightDataCallCapExceeded
    client = BrightDataClient(cap=0)
    try:
        with pytest.raises(BrightDataCallCapExceeded):
            async with respx.mock(base_url="https://api.brightdata.com"):
                await client.serp_search("anything")
    finally:
        await client.aclose()
