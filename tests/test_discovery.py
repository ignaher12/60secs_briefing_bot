import asyncio
import pytest
from wedge.discovery import find_candidates
from wedge.types import PlannerOutput

class FakeBD:
    def __init__(self):
        self.queries = []
    async def serp_search(self, q):
        self.queries.append(q)
        return [
            {"title": "Asana vs Trello", "link": "https://x", "description": "Asana and Trello compared"},
            {"title": "ClickUp alternative", "link": "https://y", "description": "ClickUp is popular"},
        ]

class FakeLLM:
    def call_json(self, **kw):
        return {"products": ["Asana", "Trello", "ClickUp"]}

@pytest.mark.asyncio
async def test_find_candidates_aggregates_mentions():
    plan = PlannerOutput(serp_queries=["q1", "q2"], target_subreddits=[], g2_category_hints=[])
    bd = FakeBD()
    out = await find_candidates(plan, bd=bd, llm=FakeLLM())
    names = {c.name for c in out}
    assert {"Asana", "Trello", "ClickUp"} <= names
    assert len(bd.queries) == 2
    # All products mentioned at least once per query
    asana = next(c for c in out if c.name == "Asana")
    assert asana.mention_count >= 2


class ConcurrencyBD:
    def __init__(self):
        self.in_flight = 0
        self.max_in_flight = 0
    async def serp_search(self, q):
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        await asyncio.sleep(0.05)
        self.in_flight -= 1
        return [{"title": "Asana", "link": "https://x", "description": "Asana"}]


@pytest.mark.asyncio
async def test_find_candidates_runs_serp_queries_concurrently():
    plan = PlannerOutput(serp_queries=["q1", "q2", "q3"], target_subreddits=[], g2_category_hints=[])
    bd = ConcurrencyBD()
    await find_candidates(plan, bd=bd, llm=FakeLLM())
    assert bd.max_in_flight > 1
