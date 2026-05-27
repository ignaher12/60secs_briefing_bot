# Wedge — Market Opportunity Brief Generator

Hackathon submission for Bright Data GTM Intelligence track.

## Run locally

1. Copy `.env.example` to `.env` and fill in API keys.
2. `python -m venv .venv && .venv\Scripts\pip install -e ".[dev]"`
3. `.venv\Scripts\playwright install chromium` (one-time)
4. `.venv\Scripts\uvicorn wedge.app:app --reload`
5. Open http://localhost:8000 and paste a product idea.

## Run tests

`.venv\Scripts\pytest -v`

All tests use saved Bright Data fixtures — no quota burn.

## Architecture

See `docs/superpowers/specs/2026-05-25-wedge-design.md`.
