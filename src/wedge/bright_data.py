import httpx
from wedge.config import load_config

class BrightDataCallCapExceeded(Exception):
    pass

class BrightDataClient:
    def __init__(self, cap: int | None = None):
        self.cfg = load_config()
        self.cap = cap if cap is not None else self.cfg.bright_data_call_cap
        self.call_count = 0
        self._client = httpx.AsyncClient(timeout=60.0)

    def _bump(self):
        self.call_count += 1
        if self.call_count > self.cap:
            raise BrightDataCallCapExceeded(f"Exceeded {self.cap} Bright Data calls")

    async def serp_search(self, query: str) -> list[dict]:
        self._bump()
        resp = await self._client.post(
            "https://api.brightdata.com/request",
            headers={"Authorization": f"Bearer {self.cfg.bright_data_token}"},
            json={
                "zone": self.cfg.bright_data_serp_zone,
                "url": f"https://www.google.com/search?q={query}&brd_json=1",
                "format": "raw",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("organic", [])

    async def aclose(self):
        await self._client.aclose()
