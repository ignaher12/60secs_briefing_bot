import pytest
from wedge.g2_confirm import confirm_on_g2
from wedge.types import Candidate

class FakeBD:
    def __init__(self, html_by_url):
        self.html_by_url = html_by_url
        self.calls = []
    async def browser_render(self, url):
        self.calls.append(url)
        return self.html_by_url.get(url, "<html></html>")

@pytest.mark.asyncio
async def test_confirm_keeps_only_real_g2_entries(fixtures_dir):
    html = (fixtures_dir / "g2_asana.html").read_text()
    bd = FakeBD({"https://www.g2.com/products/asana/reviews": html})
    candidates = [
        Candidate(name="Asana", mention_count=5),
        Candidate(name="NotARealThing9999", mention_count=3),
    ]
    out = await confirm_on_g2(candidates, bd=bd, max_keep=5)
    assert len(out) == 1
    assert out[0].name == "Asana"
    assert out[0].review_count == 11234
    assert out[0].avg_rating == 4.3
