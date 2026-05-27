import json, pytest
from fastapi.testclient import TestClient
from wedge.types import PlannerOutput, Candidate, Competitor, Complaint, Brief

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("WEDGE_DB_PATH", ":memory:")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("BRIGHT_DATA_API_TOKEN", "test")
    monkeypatch.setenv("BRIGHT_DATA_SERP_ZONE", "test")
    monkeypatch.setenv("BRIGHT_DATA_UNLOCKER_ZONE", "test")
    monkeypatch.setenv("BRIGHT_DATA_BROWSER_WS", "ws://test")
    import wedge.app as app_mod, wedge.orchestrator as orch
    app_mod._db = None
    monkeypatch.setenv("WEDGE_DB_PATH", ":memory:")

    async def fake_plan(idea, llm): return PlannerOutput(serp_queries=["q"], target_subreddits=["r"], g2_category_hints=[])
    async def fake_find(plan, *, bd, llm): return [Candidate(name="Asana", mention_count=2)]
    async def fake_confirm(c, *, bd, max_keep=5): return [Competitor(name="Asana", g2_url="u", review_count=1, avg_rating=4.0)]
    async def fake_mine(c, p, *, bd): return [Complaint(competitor="Asana", source="g2", url="u", excerpt="slow", sentiment_hint="g2-1-star")]
    def fake_synth(*, idea, competitors, complaints, llm=None, partial=False):
        return Brief(idea=idea, tldr="T", competitor_table=competitors, themes=[], gaps=["G"], positioning=["P"], partial=False)

    monkeypatch.setattr(orch, "_plan", fake_plan)
    monkeypatch.setattr(orch, "_find", fake_find)
    monkeypatch.setattr(orch, "_confirm", fake_confirm)
    monkeypatch.setattr(orch, "_mine", fake_mine)
    monkeypatch.setattr(orch, "_synthesize", fake_synth)

    class FakeBD:
        call_count = 0
        async def aclose(self): pass
    monkeypatch.setattr(app_mod, "BrightDataClient", lambda: FakeBD())
    monkeypatch.setattr(app_mod, "LLMClient", lambda: object())
    return TestClient(app_mod.app)

def test_end_to_end_flow(client):
    r = client.post("/generate", data={"idea": "AI notes"})
    assert r.status_code == 200
    job_id = r.text.split('/stream/')[1].split('"')[0]

    with client.stream("GET", f"/stream/{job_id}") as s:
        events = []
        for line in s.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
                if events[-1]["name"] in ("brief_ready", "error"):
                    break
    names = [e["name"] for e in events]
    assert "brief_ready" in names

    r = client.get(f"/brief/{job_id}")
    assert r.status_code == 200
    assert "Asana" in r.text
