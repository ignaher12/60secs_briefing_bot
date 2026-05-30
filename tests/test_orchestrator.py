import asyncio, json, pytest
from wedge.orchestrator import run_pipeline, Event
from wedge.db import Database
from wedge.types import PlannerOutput, Candidate, Competitor, Complaint, Brief

class FakeBD:
    call_count = 0

class FakeLLM: pass

@pytest.mark.asyncio
async def test_pipeline_runs_all_steps_and_emits_events(monkeypatch):
    db = Database(":memory:"); db.init_schema()
    jid = db.create_job(idea="AI notes")

    async def fake_plan(idea, llm=None):
        return PlannerOutput(serp_queries=["q"], target_subreddits=["r/x"], g2_category_hints=[])
    async def fake_find(plan, *, bd, llm):
        return [Candidate(name="Asana", mention_count=3)]
    async def fake_confirm(cands, *, bd, max_keep=5):
        return [Competitor(name="Asana", g2_url="u", review_count=10, avg_rating=4.0)]
    async def fake_mine(competitor, plan, *, bd):
        return [Complaint(competitor="Asana", source="g2", url="u", excerpt="slow", sentiment_hint="g2-1-star")]
    def fake_synth(*, idea, competitors, complaints, llm=None, partial=False):
        return Brief(idea=idea, tldr="t", competitor_table=competitors, themes=[], gaps=[], positioning=[], partial=partial)

    import wedge.orchestrator as orch
    monkeypatch.setattr(orch, "_plan", lambda idea, llm: fake_plan(idea, llm))
    monkeypatch.setattr(orch, "_find", fake_find)
    monkeypatch.setattr(orch, "_confirm", fake_confirm)
    monkeypatch.setattr(orch, "_mine", fake_mine)
    monkeypatch.setattr(orch, "_synthesize", fake_synth)

    events: list[Event] = []
    async for ev in run_pipeline(job_id=jid, db=db, bd=FakeBD(), llm=FakeLLM()):
        events.append(ev)

    names = [e.name for e in events]
    assert names == ["planning_done", "candidates_found", "competitors_confirmed",
                     "complaints_mined", "brief_ready"]
    assert db.get_job(jid)["status"] == "complete"
    assert json.loads(db.get_job(jid)["brief_json"])["tldr"] == "t"


@pytest.mark.asyncio
async def test_pipeline_mines_competitors_concurrently(monkeypatch):
    db = Database(":memory:"); db.init_schema()
    jid = db.create_job(idea="x")
    state = {"in_flight": 0, "max": 0}

    async def fake_plan(idea, llm=None):
        return PlannerOutput(serp_queries=["q"], target_subreddits=["r/x"], g2_category_hints=[])
    async def fake_find(plan, *, bd, llm):
        return [Candidate(name="A", mention_count=1)]
    async def fake_confirm(cands, *, bd, max_keep=5):
        return [Competitor(name=f"C{i}", g2_url="u", review_count=1, avg_rating=4.0) for i in range(3)]
    async def fake_mine(competitor, plan, *, bd):
        state["in_flight"] += 1
        state["max"] = max(state["max"], state["in_flight"])
        await asyncio.sleep(0.05)
        state["in_flight"] -= 1
        return []
    def fake_synth(**kw):
        return Brief(idea="x", tldr="t", competitor_table=[], themes=[], gaps=[], positioning=[], partial=False)

    import wedge.orchestrator as orch
    monkeypatch.setattr(orch, "_plan", lambda idea, llm: fake_plan(idea, llm))
    monkeypatch.setattr(orch, "_find", fake_find)
    monkeypatch.setattr(orch, "_confirm", fake_confirm)
    monkeypatch.setattr(orch, "_mine", fake_mine)
    monkeypatch.setattr(orch, "_synthesize", fake_synth)

    async for _ in run_pipeline(job_id=jid, db=db, bd=FakeBD(), llm=FakeLLM()):
        pass

    assert state["max"] > 1
