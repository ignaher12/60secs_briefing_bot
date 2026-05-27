import asyncio, json
from dataclasses import asdict
from pathlib import Path
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from wedge.db import Database
from wedge.config import load_config
from wedge.bright_data import BrightDataClient
from wedge.llm import LLMClient
from wedge.orchestrator import run_pipeline

BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / "templates"))

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")

_db: Database | None = None
_event_queues: dict[str, asyncio.Queue] = {}


def get_db() -> Database:
    global _db
    if _db is None:
        cfg = load_config()
        _db = Database(cfg.db_path)
        _db.init_schema()
    return _db


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/generate")
async def generate(request: Request, idea: str = Form(...)):
    db = get_db()
    job_id = db.create_job(idea=idea)
    queue: asyncio.Queue = asyncio.Queue()
    _event_queues[job_id] = queue
    asyncio.create_task(_run_job(job_id, queue))
    return templates.TemplateResponse(
        request, "progress.html", {"job_id": job_id, "idea": idea}
    )


async def _run_job(job_id: str, queue: asyncio.Queue):
    db = get_db()
    bd = BrightDataClient()
    llm = LLMClient()
    try:
        async for event in run_pipeline(job_id=job_id, db=db, bd=bd, llm=llm):
            await queue.put(event)
    finally:
        await queue.put(None)
        await bd.aclose()


@app.get("/stream/{job_id}")
async def stream(job_id: str):
    queue = _event_queues.get(job_id)
    if queue is None:
        return StreamingResponse(iter([]), media_type="text/event-stream")

    async def gen():
        while True:
            event = await queue.get()
            if event is None:
                break
            payload = json.dumps({"name": event.name, "data": event.data})
            yield f"data: {payload}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/brief/{job_id}", response_class=HTMLResponse)
def brief(request: Request, job_id: str):
    db = get_db()
    job = db.get_job(job_id)
    if not job or not job.get("brief_json"):
        return HTMLResponse("Not ready", status_code=404)
    brief = json.loads(job["brief_json"])
    brief["job_id"] = job_id
    return templates.TemplateResponse(request, "brief.html", {"brief": brief})


@app.post("/watch/{job_id}")
def watch(job_id: str):
    get_db().set_watched(job_id, True)
    return RedirectResponse(f"/brief/{job_id}", status_code=303)
