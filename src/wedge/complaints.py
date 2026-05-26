import re
from html.parser import HTMLParser
from wedge.types import Competitor, Complaint, PlannerOutput

_REVIEW_RE = re.compile(
    r'<article class="review" data-rating="([12])"[^>]*>.*?<p>(.*?)</p>.*?datetime="(\d{4}-\d{2}-\d{2})"',
    re.DOTALL,
)

class _TextExtractor(HTMLParser):
    def __init__(self): super().__init__(); self.parts = []
    def handle_data(self, data): self.parts.append(data)

def _strip_html(s: str) -> str:
    ex = _TextExtractor(); ex.feed(s); return " ".join(" ".join(ex.parts).split())

async def _mine_g2(competitor: Competitor, *, bd) -> list[Complaint]:
    url = f"{competitor.g2_url}?order=most_recent&filters[ratings][]=1&filters[ratings][]=2"
    try:
        html = await bd.browser_render(url)
    except Exception:
        return []
    out: list[Complaint] = []
    for rating, body, date in _REVIEW_RE.findall(html):
        out.append(Complaint(
            competitor=competitor.name, source="g2", url=url,
            excerpt=_strip_html(body)[:500],
            sentiment_hint=f"g2-{rating}-star", date=date,
        ))
    return out

async def _mine_reddit_via_serp(competitor: Competitor, plan: PlannerOutput, *, bd) -> list[Complaint]:
    query = f"{competitor.name} alternative OR sucks OR vs"
    try:
        results = await bd.serp_search(query)
    except Exception:
        return []
    reddit_urls = [r["link"] for r in results if "reddit.com" in r.get("link","")][:3]
    out: list[Complaint] = []
    for url in reddit_urls:
        try:
            body = await bd.fetch(url)
        except Exception:
            continue
        out.append(Complaint(
            competitor=competitor.name, source="reddit", url=url,
            excerpt=_strip_html(body)[:500],
            sentiment_hint="reddit-thread",
        ))
    return out

async def mine_complaints(competitor: Competitor, plan: PlannerOutput, *, bd) -> list[Complaint]:
    g2 = await _mine_g2(competitor, bd=bd)
    rd = await _mine_reddit_via_serp(competitor, plan, bd=bd)
    return g2 + rd
