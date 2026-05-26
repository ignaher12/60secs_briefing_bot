import re
from wedge.types import Candidate, Competitor

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_RATING_RE = re.compile(r'ratingValue"\s+content="([\d.]+)"')
_COUNT_RE = re.compile(r'reviewCount"\s+content="(\d+)"')

def _slug(name: str) -> str:
    return _SLUG_RE.sub("-", name.lower()).strip("-")

def _g2_url(name: str) -> str:
    return f"https://www.g2.com/products/{_slug(name)}/reviews"

async def confirm_on_g2(candidates: list[Candidate], *, bd, max_keep: int = 5) -> list[Competitor]:
    confirmed: list[Competitor] = []
    for c in candidates:
        url = _g2_url(c.name)
        try:
            html = await bd.browser_render(url)
        except Exception:
            continue
        r = _RATING_RE.search(html)
        n = _COUNT_RE.search(html)
        if not r or not n:
            continue
        confirmed.append(Competitor(
            name=c.name, g2_url=url,
            review_count=int(n.group(1)), avg_rating=float(r.group(1)),
        ))
        if len(confirmed) >= max_keep:
            break
    return confirmed
