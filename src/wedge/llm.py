import json, re
from anthropic import Anthropic
from wedge.config import load_config

MODELS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

class LLMClient:
    def __init__(self, client=None):
        cfg = load_config()
        self._client = client or Anthropic(api_key=cfg.anthropic_api_key)

    def call_json(self, *, model: str, system: str, user: str, max_tokens: int = 4096) -> dict:
        resp = self._client.messages.create(
            model=MODELS[model],
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        raw = resp.content[0].text.strip()
        cleaned = _FENCE_RE.sub("", raw).strip()
        return json.loads(cleaned)
