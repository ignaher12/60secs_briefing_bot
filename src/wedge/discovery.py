import asyncio
from collections import Counter
from wedge.types import Candidate, PlannerOutput

SYSTEM = """Extract distinct product / company names from search results.
Return ONLY JSON: {"products": [string, ...]}
Exclude generic terms, blog names, and review-site names (G2, Capterra, TrustRadius)."""

async def find_candidates(plan: PlannerOutput, *, bd, llm, max_candidates: int = 10) -> list[Candidate]:
    counter: Counter[str] = Counter()
    sources: dict[str, set[str]] = {}
    results_per_query = await asyncio.gather(
        *(bd.serp_search(q) for q in plan.serp_queries)
    )
    for results in results_per_query:
        if not results:
            continue
        joined = "\n".join(f"- {r.get('title','')} — {r.get('description','')}" for r in results)
        payload = llm.call_json(model="haiku", system=SYSTEM, user=joined)
        for name in payload.get("products", []):
            counter[name] += 1
            sources.setdefault(name, set()).update(
                r["link"] for r in results
                if name.lower() in (r.get("title", "") + r.get("description", "")).lower()
            )
    return [
        Candidate(name=n, mention_count=c, source_urls=sorted(sources.get(n, [])))
        for n, c in counter.most_common(max_candidates)
    ]
