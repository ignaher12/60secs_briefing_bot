from wedge.types import (
    PlannerOutput, Candidate, Competitor, Complaint, ComplaintTheme, Brief
)

def test_planner_output_basic():
    p = PlannerOutput(
        serp_queries=["best pm tool"],
        target_subreddits=["r/projectmanagement"],
        g2_category_hints=["project-management"],
    )
    assert p.serp_queries == ["best pm tool"]

def test_candidate_basic():
    c = Candidate(name="Asana", mention_count=4, source_urls=["https://x"])
    assert c.mention_count == 4

def test_competitor_basic():
    c = Competitor(name="Asana", g2_url="https://g2.com/p/asana", review_count=12345, avg_rating=4.3)
    assert c.review_count == 12345

def test_complaint_basic():
    c = Complaint(competitor="Asana", source="g2", url="https://x", excerpt="too slow", sentiment_hint="negative", date="2026-03-01")
    assert c.source == "g2"

def test_brief_basic():
    b = Brief(idea="x", tldr="t", competitor_table=[], themes=[], gaps=[], positioning=[], partial=False)
    assert b.partial is False
