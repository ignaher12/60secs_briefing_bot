import asyncio
import re
from wedge.types import Candidate, Competitor

_SLUG_RE = re.compile(r"[^a-z0-9]+")
# G2's schema.org markup puts `content` before `itemprop`, e.g.
# <meta content="4.4" itemprop="ratingValue">
_RATING_RE = re.compile(r'content="([\d.]+)"\s+itemprop="ratingValue"')
_COUNT_RE = re.compile(r'content="(\d+)"\s+itemprop="reviewCount"')

def _slug(name: str) -> str:
    return _SLUG_RE.sub("-", name.lower()).strip("-")

def _g2_url(name: str) -> str:
    return f"https://www.g2.com/products/{_slug(name)}/reviews"

async def _fetch_or_none(bd, url: str) -> str | None:
    try:
        return await bd.fetch(url)
    except Exception:
        return None

async def confirm_on_g2(candidates: list[Candidate], *, bd, max_keep: int = 5) -> list[Competitor]:
    urls = [_g2_url(c.name) for c in candidates]
    htmls = await asyncio.gather(*(_fetch_or_none(bd, url) for url in urls))
    confirmed: list[Competitor] = []
    for c, url, html in zip(candidates, urls, htmls):
        if html is None:
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
