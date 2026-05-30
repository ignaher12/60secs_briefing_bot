import httpx
from urllib.parse import urlencode
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
        qs = urlencode({"q": query, "brd_json": 1})
        resp = await self._client.post(
            "https://api.brightdata.com/request",
            headers={"Authorization": f"Bearer {self.cfg.bright_data_token}"},
            json={
                "zone": self.cfg.bright_data_serp_zone,
                "url": f"https://www.google.com/search?{qs}",
                "format": "raw",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("organic", [])

    async def fetch(self, url: str) -> str:
        self._bump()
        resp = await self._client.post(
            "https://api.brightdata.com/request",
            headers={"Authorization": f"Bearer {self.cfg.bright_data_token}"},
            json={
                "zone": self.cfg.bright_data_unlocker_zone,
                "url": url,
                "format": "raw",
            },
        )
        resp.raise_for_status()
        return resp.text

    def _playwright_factory(self):
        from playwright.async_api import async_playwright
        return async_playwright()

    async def browser_render(self, url: str) -> str:
        self._bump()
        async with self._playwright_factory() as pw:
            browser = await pw.chromium.connect_over_cdp(self.cfg.bright_data_browser_ws)
            try:
                ctx = await browser.new_context()
                try:
                    page = await ctx.new_page()
                    try:
                        await page.goto(url, timeout=60000)
                        return await page.content()
                    finally:
                        await page.close()
                finally:
                    await ctx.close()
            finally:
                await browser.close()

    async def aclose(self):
        await self._client.aclose()
