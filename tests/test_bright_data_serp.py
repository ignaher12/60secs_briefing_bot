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
async def test_serp_search_url_encodes_query_with_spaces(fixtures_dir):
    payload = json.loads((fixtures_dir / "serp_pm_tool.json").read_text())
    async with respx.mock(base_url="https://api.brightdata.com") as mock:
        route = mock.post("/request").mock(return_value=httpx.Response(200, json=payload))
        client = BrightDataClient()
        try:
            await client.serp_search("best used car marketplaces")
        finally:
            await client.aclose()
        sent_url = json.loads(route.calls.last.request.content)["url"]
    # Bright Data rejects URLs with raw spaces ("must be a valid uri")
    assert " " not in sent_url
    assert "best+used+car+marketplaces" in sent_url or "best%20used%20car%20marketplaces" in sent_url
    assert "brd_json=1" in sent_url


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
