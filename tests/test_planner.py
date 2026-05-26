import pytest
from wedge.planner import plan
from wedge.types import PlannerOutput

class FakeLLM:
    def __init__(self, payload): self.payload = payload; self.calls = []
    def call_json(self, **kw): self.calls.append(kw); return self.payload

def test_plan_happy_path():
    fake = FakeLLM({
        "serp_queries": ["best ai meeting notes", "ai meeting notes alternatives"],
        "target_subreddits": ["r/sales", "r/saas"],
        "g2_category_hints": ["ai-sales-assistant"],
    })
    out = plan("AI meeting note-taker for sales", llm=fake)
    assert isinstance(out, PlannerOutput)
    assert "best ai meeting notes" in out.serp_queries
    assert fake.calls[0]["model"] == "haiku"

def test_plan_fallback_on_malformed_llm():
    class Bad:
        def call_json(self, **kw): raise ValueError("bad json")
    out = plan("anything", llm=Bad())
    assert out.serp_queries  # non-empty fallback
    assert out.target_subreddits
