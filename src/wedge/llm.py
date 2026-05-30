import json, re
from openai import OpenAI
from wedge.config import load_config

# NVIDIA build exposes an OpenAI-compatible API. Both pipeline roles use the
# same Llama model; the dict keeps the planner/synth split swappable.
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

MODELS = {
    "haiku": "meta/llama-3.3-70b-instruct",
    "sonnet": "meta/llama-3.3-70b-instruct",
}

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

class LLMClient:
    def __init__(self, client=None):
        cfg = load_config()
        self._client = client or OpenAI(
            base_url=NVIDIA_BASE_URL, api_key=cfg.nvidia_api_key
        )

    def call_json(self, *, model: str, system: str, user: str, max_tokens: int = 4096) -> dict:
        resp = self._client.chat.completions.create(
            model=MODELS[model],
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        raw = resp.choices[0].message.content.strip()
        cleaned = _FENCE_RE.sub("", raw).strip()
        return json.loads(cleaned)
