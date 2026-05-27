import json, pytest
from wedge.watcher import diff_briefs, format_delta_email
from wedge.types import Brief, ComplaintTheme, Competitor

def _brief(themes):
    return Brief(idea="x", tldr="t",
                 competitor_table=[Competitor(name="Asana", g2_url="u", review_count=1, avg_rating=4.0)],
                 themes=themes, gaps=[], positioning=[], partial=False)

def test_diff_finds_new_themes():
    old = _brief([ComplaintTheme(label="Slow mobile", frequency=3, severity="medium", sample_quotes=[], competitors_affected=["Asana"])])
    new = _brief([
        ComplaintTheme(label="Slow mobile", frequency=8, severity="high", sample_quotes=[], competitors_affected=["Asana"]),
        ComplaintTheme(label="Pricing surprises", frequency=4, severity="medium", sample_quotes=[], competitors_affected=["Asana"]),
    ])
    delta = diff_briefs(old, new)
    assert "Pricing surprises" in [t.label for t in delta["new_themes"]]
    assert any(d["label"] == "Slow mobile" and d["delta"] == 5 for d in delta["changed_frequency"])

def test_format_delta_email_is_non_empty():
    delta = {"new_themes": [ComplaintTheme(label="X", frequency=2, severity="low", sample_quotes=[], competitors_affected=[])],
             "changed_frequency": []}
    text = format_delta_email("AI notes", delta)
    assert "AI notes" in text and "X" in text
