import asyncio
from dataclasses import dataclass, asdict
from typing import Any, AsyncIterator
from wedge.planner import plan as _plan_fn
from wedge.discovery import find_candidates as _find
from wedge.g2_confirm import confirm_on_g2 as _confirm
from wedge.complaints import mine_complaints as _mine
from wedge.synthesis import synthesize as _synthesize

async def _plan(idea, llm):
    return _plan_fn(idea, llm=llm)

@dataclass
class Event:
    name: str
    data: dict[str, Any]

def _dump(obj):
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    if isinstance(obj, list):
        return [_dump(o) for o in obj]
    return obj

async def run_pipeline(*, job_id: str, db, bd, llm) -> AsyncIterator[Event]:
    try:
        db.set_status(job_id, "planning")
        plan = await _plan(db.get_job(job_id)["idea"], llm)
        db.save_artifact(job_id, "planner_output_json", _dump(plan))
        yield Event("planning_done", {"queries": plan.serp_queries})

        db.set_status(job_id, "discovery")
        candidates = await _find(plan, bd=bd, llm=llm)
        db.save_artifact(job_id, "candidates_json", _dump(candidates))
        yield Event("candidates_found", {"count": len(candidates), "names": [c.name for c in candidates]})

        db.set_status(job_id, "confirming")
        competitors = await _confirm(candidates, bd=bd)
        db.save_artifact(job_id, "competitors_json", _dump(competitors))
        yield Event("competitors_confirmed", {"names": [c.name for c in competitors]})

        db.set_status(job_id, "mining")
        mined = await asyncio.gather(*(_mine(comp, plan, bd=bd) for comp in competitors))
        all_complaints = []
        for comp, complaints in zip(competitors, mined):
            all_complaints.extend(complaints)
            yield Event("complaints_mined", {"competitor": comp.name, "count": len(complaints)})
        db.save_artifact(job_id, "complaints_json", _dump(all_complaints))

        db.set_status(job_id, "synthesizing")
        partial = getattr(bd, "call_cap_hit", False)
        brief = _synthesize(idea=db.get_job(job_id)["idea"],
                            competitors=competitors, complaints=all_complaints,
                            llm=llm, partial=partial)
        db.save_artifact(job_id, "brief_json", _dump(brief))
        db.set_status(job_id, "complete")
        yield Event("brief_ready", {"job_id": job_id})

        if hasattr(bd, "call_count"):
            db.bump_calls(job_id, bd.call_count)
    except Exception as e:
        db.set_status(job_id, "failed")
        yield Event("error", {"message": str(e)})
