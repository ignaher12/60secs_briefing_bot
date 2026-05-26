# Wedge — Market Opportunity Brief Generator

**Status:** Design approved, ready for implementation planning
**Date:** 2026-05-25
**Hackathon track:** Bright Data — GTM Intelligence (Track 1)

---

## 1. Product framing

**What it is:** A web app where a user pastes a concise product idea (e.g. *"AI meeting note-taker for sales teams"*) and gets back, in roughly sixty seconds, a single-page **Market Opportunity Brief** containing:

1. The dominant competitors in that space
2. Structured customer complaints about each
3. Opportunity gaps synthesized by an LLM
4. Suggested positioning angles

**Who it's for:**
- **Founders / indie hackers** validating an idea — read top-down for "is there a wedge?"
- **PMs / PMMs** sharpening positioning — read competitor-by-competitor for "how do I differentiate?"

The same artifact serves both audiences.

**Core loop:** One-shot generation now, plus a "watch this idea" toggle that re-runs weekly and emails a delta summary.

**Explicit non-goals (hackathon scope cuts):**
- Not an outreach tool — no draft emails, no CRM push
- No de-anonymization of Reddit users
- No Twitter/X or LinkedIn scraping
- No CRM integrations
- No multi-user / team features

**Optimization axis:** Novel use case + end-to-end polish, with a light agentic flavor. Technical depth on Bright Data is deliberately *not* the wow axis (quota is limited).

---

## 2. Architecture

Lightly agentic: an LLM planner makes real upstream decisions, then a deterministic execution pipeline runs, then an LLM synthesizer writes the brief. Two LLM call sites only.

```
[User idea]
     │
     ▼
1. Planner (LLM)            → SERP queries, target subreddits, G2 category hints
     │
     ▼
2. Competitor Discovery     → Bright Data SERP API, rank candidates by mention frequency
     │
     ▼
3. G2 Confirmation          → Bright Data Scraping Browser, keep ≤5 with real category presence
     │
     ▼
4. Complaint Mining (lean)  → Per competitor: G2 1-2★ reviews + SERP "alternative/sucks/vs" + top Reddit threads
     │
     ▼
5. Synthesis (LLM)          → Cluster, rank, surface gaps, draft positioning
     │
     ▼
6. Render Brief             → Markdown → web UI, persisted in SQLite
```

**Tech stack:**

| Layer | Choice | Reason |
|---|---|---|
| Backend | Python + FastAPI | Best Bright Data + LLM tooling story |
| LLM (planner) | Claude Haiku 4.5 | Cheap, structured output, fast |
| LLM (synthesis) | Claude Sonnet 4.6 | Quality matters here |
| Frontend | Server-rendered HTML + minimal JS for SSE | No build step burning hackathon time |
| Queue | None — synchronous request with SSE streaming | ~60s job fits inside a streamed HTTP response |
| DB | SQLite (stdlib `sqlite3`) | Zero-ops, enables weekly-rerun diffing |

---

## 3. Components

Each module owns one job, communicates via dataclasses, has no shared global state, and is unit-testable with saved Bright Data fixtures.

### 3.1 `planner.py` — LLM planning
- **Input:** raw idea string
- **Output:** `PlannerOutput(serp_queries: list[str], target_subreddits: list[str], g2_category_hints: list[str])`
- **How:** one Claude Haiku call with a structured-output schema
- **Why isolated:** swap models / tune prompts without touching scrapers

### 3.2 `discovery.py` — Competitor discovery via SERP
- **Input:** SERP queries from planner
- **Output:** `list[Candidate(name, mention_count, source_urls)]`
- **How:** Bright Data SERP API → extract org/product names from titles + snippets (regex first pass, small LLM extraction pass on snippets to catch what regex misses)
- **Why isolated:** SERP is the single biggest Bright Data line item; isolating it makes the budget gate trivial

### 3.3 `g2_confirm.py` — G2 lookup + filtering
- **Input:** candidates + category hints
- **Output:** `list[Competitor(name, g2_url, review_count, avg_rating)]`, capped at 5
- **How:** Bright Data Scraping Browser, one page load per candidate (G2 is JS- and anti-bot-heavy)
- **Why isolated:** G2's HTML changes; only this module breaks when it does

### 3.4 `complaints.py` — Lean complaint mining
- **Input:** confirmed competitors
- **Output:** per competitor, `list[Complaint(source, url, excerpt, sentiment_hint, date)]`
- **How:** for each competitor:
  1. Scrape G2 1-2★ reviews (recent) via Scraping Browser
  2. SERP for `"[name] alternative OR sucks OR vs"`
  3. Scrape top 3 Reddit threads from results via Web Unlocker
- **Why isolated:** the future "deepen this competitor" feature just calls this with different params

### 3.5 `synthesis.py` — LLM synthesis
- **Input:** raw complaints + competitor list
- **Output:** `Brief(tldr, competitor_table, themes, gaps, positioning)`
- **How:**
  - Pre-cluster complaints by embedding similarity *before* the LLM call to reduce tokens
  - Single Claude Sonnet call with strict output schema
- **Why isolated:** pure function, no I/O — prompt iteration is fast and free

### 3.6 `app.py` — FastAPI + SSE + storage
- **Endpoints:**
  - `POST /generate` — start a job, return job_id
  - `GET /stream/{job_id}` — SSE progress events
  - `GET /brief/{job_id}` — rendered brief HTML
  - `POST /watch/{job_id}` — enable weekly rerun
- **DB schema:** `jobs(id, idea, status, created_at, planner_output_json, candidates_json, competitors_json, complaints_json, brief_json, watched, bright_data_calls)`

---

## 4. Data flow & state

```
POST /generate {idea}
  │
  ├─ create job row (status=planning)
  ├─ open SSE stream
  │
  ├─ planner.plan(idea) ──────────────► event: "planning_done"
  ├─ discovery.find(queries) ─────────► event: "candidates_found" (count)
  ├─ g2_confirm.confirm(candidates) ──► event: "competitors_confirmed" (names)
  ├─ complaints.mine(competitors) ────► event: "complaints_mined" (per competitor)
  ├─ synthesis.synthesize(...) ───────► event: "brief_ready"
  │
  └─ status=complete, close stream
```

**Per-step persistence.** Each step writes output before the next runs. This buys two things:

1. **Cheap iteration.** If synthesis fails or its prompt is bad, retry just step 5 against persisted complaints — no re-scraping, no Bright Data burn.
2. **Streamed demo narrative.** SSE events make the perceived intelligence much higher than a generic 60s spinner.

**"Watch this idea" weekly re-run.** A scheduled job re-runs steps 2–5 (reuses the original planner output), diffs the new brief against the prior brief, and emails a delta summary highlighting new themes and frequency shifts.

### Bright Data budget per job

| Step | Calls (target) |
|---|---|
| Planner | 0 |
| Discovery | 2–3 SERP |
| G2 confirm | 5–7 Scraping Browser |
| Complaints | 15–20 (5 competitors × ~3–4) |
| **Total target** | **~25–30** |
| **Hard cap** | **40** — abort remaining steps, run synthesis on what we have, emit `partial: true` |

---

## 5. Error handling

Pipeline degrades gracefully — a partial brief is better than a 500.

| Step | Failure mode | Handling |
|---|---|---|
| Planner | Malformed LLM JSON | One retry with stricter schema reminder; fall back to a hardcoded generic plan |
| Discovery | Zero brand mentions | Mark job `degraded`, surface to user: "try a more specific idea" |
| G2 confirm | Candidate has no G2 page | Drop silently; need ≥2 confirmed; if <2, fall back to SERP-only confirmation |
| G2 confirm | Anti-bot trip | One retry with Scraping Browser session reset; if still failing, skip with flag in brief |
| Complaints | Reddit thread 404 / removed | Skip, log, continue |
| Complaints | All sources empty for one competitor | Keep competitor in brief; flag "limited public criticism" — that's a *signal* |
| Synthesis | LLM context exceeded | Tighten clustering threshold, drop oldest complaints, retry once |
| Budget cap hit | Bright Data calls > 40 | Abort remaining steps, synthesize what we have, mark `partial: true` |

---

## 6. Testing

- **Unit tests with fixtures.** Each module has `tests/fixtures/` containing real Bright Data responses captured during dev. Tests run offline, zero quota burn.
- **One end-to-end test** against a known idea ("project management tool") with all Bright Data calls mocked from fixtures.
- **Manual smoke ritual.** Before demo: run three real ideas of varying specificity, eyeball the briefs. No automated synthesis-quality check — that's a human judgment.

---

## 7. Demo arc (3 minutes)

1. **Hook (15s)** — "Founders waste weeks on competitive research. Watch this." Paste idea live.
2. **The reveal (45s)** — SSE stream narrates: planner picks subreddits, discovery finds candidates, G2 confirms, complaints stream in per competitor.
3. **The brief (60s)** — Scroll through: competitor table, complaint themes with real quotes + source links, opportunity gaps, positioning angles.
4. **The "click" moment (30s)** — Hit "watch this idea" → show pre-generated mock of the weekly delta email.
5. **Close (30s)** — "Two LLM calls, ~25 Bright Data calls, ~60 seconds, one founder less stuck."

**Three pre-tested ideas** (B2B SaaS, consumer, dev tool) — pick the strongest on demo day.

---

## 8. Open items for the implementation plan

- Exact Claude prompts (planner + synthesizer) — drafted during TDD on synthesis module
- Embedding model for pre-clustering (likely a small local model or Voyage)
- Email delivery for "watch this idea" (Resend / SES / mocked for demo)
- Choice of Bright Data SDK vs raw HTTP (depends on Python SDK quality at time of build)
