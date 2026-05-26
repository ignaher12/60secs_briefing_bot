import json, pytest
from wedge.llm import LLMClient

class FakeMessages:
    def __init__(self, payload): self._payload = payload
    def create(self, **kw):
        class R:
            content = [type("B", (), {"text": json.dumps(self._payload)})()]
        return R()

class FakeAnthropic:
    def __init__(self, payload): self.messages = FakeMessages(payload)

def test_call_json_returns_parsed_dict():
    fake = FakeAnthropic({"hello": "world"})
    llm = LLMClient(client=fake)
    out = llm.call_json(model="haiku", system="s", user="u")
    assert out == {"hello": "world"}

def test_call_json_strips_fences():
    fake = FakeAnthropic({"x": 1})
    # Wrap content in ```json fences via a custom fake
    class W:
        content = [type("B", (), {"text": "```json\n{\"x\": 1}\n```"})()]
    class FA:
        messages = type("M", (), {"create": lambda self, **kw: W()})()
    llm = LLMClient(client=FA())
    out = llm.call_json(model="haiku", system="s", user="u")
    assert out == {"x": 1}
