import asyncio
import pytest
from wedge.complaints import mine_complaints
from wedge.types import Competitor, PlannerOutput

class FakeBD:
    def __init__(self, html_by_url, serp_by_query):
        self.html_by_url = html_by_url
        self.serp_by_query = serp_by_query
        self.calls = 0
    async def browser_render(self, url):
        self.calls += 1
        return self.html_by_url.get(url, "")
    async def fetch(self, url):
        self.calls += 1
        return self.html_by_url.get(url, "<html><body>too slow</body></html>")
    async def serp_search(self, q):
        self.calls += 1
        return self.serp_by_query.get(q, [])

@pytest.mark.asyncio
async def test_mine_complaints_pulls_g2_reddit_and_serp(fixtures_dir):
    competitor = Competitor(name="Asana", g2_url="https://www.g2.com/products/asana/reviews",
                            review_count=100, avg_rating=4.0)
    plan = PlannerOutput(serp_queries=[], target_subreddits=["r/saas"], g2_category_hints=[])
    g2_reviews_html = (fixtures_dir / "g2_asana_reviews.html").read_text()
    bd = FakeBD(
        html_by_url={
            "https://www.g2.com/products/asana/reviews?order=most_recent&filters[ratings][]=1&filters[ratings][]=2": g2_reviews_html,
            "https://reddit.com/r/saas/thread1": "<html><body>asana is awful</body></html>",
        },
        serp_by_query={
            'Asana alternative OR sucks OR vs': [
                {"title": "Asana sucks", "link": "https://reddit.com/r/saas/thread1", "description": ""},
            ]
        },
    )
    out = await mine_complaints(competitor, plan, bd=bd)
    sources = {c.source for c in out}
    assert "g2" in sources
    assert "reddit" in sources
    # Only 1-2 star G2 reviews kept
    g2_excerpts = [c.excerpt for c in out if c.source == "g2"]
    assert any("mobile app crashes" in e for e in g2_excerpts)
    assert not any("Love it" in e for e in g2_excerpts)


class ConcurrencyBD:
    def __init__(self):
        self.in_flight = 0
        self.max_in_flight = 0
    async def fetch(self, url):
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        await asyncio.sleep(0.05)
        self.in_flight -= 1
        return "<html><body>some complaint text</body></html>"
    async def serp_search(self, q):
        return [{"title": "t", "link": f"https://reddit.com/r/x/{i}", "description": ""} for i in range(3)]


@pytest.mark.asyncio
async def test_mine_complaints_fetches_concurrently():
    competitor = Competitor(name="Asana", g2_url="https://www.g2.com/products/asana/reviews",
                            review_count=100, avg_rating=4.0)
    plan = PlannerOutput(serp_queries=[], target_subreddits=["r/saas"], g2_category_hints=[])
    bd = ConcurrencyBD()
    await mine_complaints(competitor, plan, bd=bd)
    assert bd.max_in_flight > 1
