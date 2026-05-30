import json, pytest
from wedge.llm import LLMClient


def _fake_openai(text):
    """Build a fake OpenAI-compatible client returning `text` as the message content."""
    class FakeCompletions:
        def create(self, **kw):
            message = type("Msg", (), {"content": text})()
            choice = type("Choice", (), {"message": message})()
            return type("Resp", (), {"choices": [choice]})()
    class FakeChat:
        completions = FakeCompletions()
    class FakeOpenAI:
        chat = FakeChat()
    return FakeOpenAI()


def test_call_json_returns_parsed_dict():
    fake = _fake_openai(json.dumps({"hello": "world"}))
    llm = LLMClient(client=fake)
    out = llm.call_json(model="haiku", system="s", user="u")
    assert out == {"hello": "world"}


def test_call_json_strips_fences():
    fake = _fake_openai('```json\n{"x": 1}\n```')
    llm = LLMClient(client=fake)
    out = llm.call_json(model="haiku", system="s", user="u")
    assert out == {"x": 1}
