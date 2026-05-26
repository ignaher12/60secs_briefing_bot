from dataclasses import dataclass, field
from typing import Literal

@dataclass
class PlannerOutput:
    serp_queries: list[str]
    target_subreddits: list[str]
    g2_category_hints: list[str]

@dataclass
class Candidate:
    name: str
    mention_count: int
    source_urls: list[str] = field(default_factory=list)

@dataclass
class Competitor:
    name: str
    g2_url: str
    review_count: int
    avg_rating: float

@dataclass
class Complaint:
    competitor: str
    source: Literal["g2", "reddit", "serp"]
    url: str
    excerpt: str
    sentiment_hint: str
    date: str | None = None

@dataclass
class ComplaintTheme:
    label: str
    frequency: int
    severity: Literal["low", "medium", "high"]
    sample_quotes: list[str]
    competitors_affected: list[str]

@dataclass
class Brief:
    idea: str
    tldr: str
    competitor_table: list[Competitor]
    themes: list[ComplaintTheme]
    gaps: list[str]
    positioning: list[str]
    partial: bool = False
