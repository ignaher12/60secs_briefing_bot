from wedge.types import PlannerOutput
from wedge.llm import LLMClient

SYSTEM = """You plan competitive research for a product idea.
Return ONLY JSON matching:
{
  "serp_queries": [string, ...],     // 3-5 Google queries to find competitors
  "target_subreddits": [string, ...],// 3-6 subreddits relevant to the audience
  "g2_category_hints": [string, ...] // 1-3 G2 category slugs guesses
}
Queries must include at least one "best X" and one "X alternatives" form."""

def _fallback(idea: str) -> PlannerOutput:
    return PlannerOutput(
        serp_queries=[f"best {idea}", f"{idea} alternatives", f"{idea} vs"],
        target_subreddits=["r/SaaS", "r/startups", "r/productivity"],
        g2_category_hints=[],
    )

def plan(idea: str, llm=None) -> PlannerOutput:
    llm = llm or LLMClient()
    try:
        data = llm.call_json(model="haiku", system=SYSTEM, user=f"Idea: {idea}")
        return PlannerOutput(
            serp_queries=data["serp_queries"],
            target_subreddits=data["target_subreddits"],
            g2_category_hints=data.get("g2_category_hints", []),
        )
    except Exception:
        return _fallback(idea)
