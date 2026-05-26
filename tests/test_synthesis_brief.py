from wedge.synthesis import synthesize
from wedge.types import Competitor, Complaint, Brief


class FakeLLM:
    def call_json(self, **kw):
        return {
            "tldr": "Market has wedges around mobile UX and pricing.",
            "themes": [
                {"label": "Mobile app instability", "frequency": 7, "severity": "high",
                 "sample_quotes": ["mobile app crashes daily"], "competitors_affected": ["Asana"]},
                {"label": "Pricing surprises", "frequency": 4, "severity": "medium",
                 "sample_quotes": ["pricing increase forced us out"], "competitors_affected": ["Asana"]},
            ],
            "gaps": ["No competitor offers a stable mobile-first experience"],
            "positioning": ["Lead with mobile-first reliability"],
        }


def test_synthesize_returns_brief():
    competitors = [Competitor(name="Asana", g2_url="u", review_count=100, avg_rating=4.0)]
    complaints = [
        Complaint(competitor="Asana", source="g2", url="u", excerpt="mobile crashes", sentiment_hint="g2-1-star"),
        Complaint(competitor="Asana", source="g2", url="u", excerpt="pricing went up", sentiment_hint="g2-2-star"),
    ]
    brief = synthesize(idea="PM tool", competitors=competitors, complaints=complaints, llm=FakeLLM())
    assert isinstance(brief, Brief)
    assert brief.tldr.startswith("Market has")
    assert len(brief.themes) == 2
    assert brief.competitor_table[0].name == "Asana"
    assert brief.partial is False


def test_synthesize_marks_partial_when_flag_set():
    brief = synthesize(idea="x", competitors=[], complaints=[], llm=FakeLLM(), partial=True)
    assert brief.partial is True
