from wedge.synthesis import cluster_complaints
from wedge.types import Complaint


def test_cluster_groups_similar_complaints():
    c = [
        Complaint(competitor="X", source="g2", url="u1", excerpt="mobile app is slow and crashes", sentiment_hint="g2-1-star"),
        Complaint(competitor="X", source="g2", url="u2", excerpt="the mobile application keeps crashing", sentiment_hint="g2-2-star"),
        Complaint(competitor="X", source="reddit", url="u3", excerpt="pricing increase pushed us out", sentiment_hint="reddit-thread"),
        Complaint(competitor="X", source="reddit", url="u4", excerpt="they raised prices and we left", sentiment_hint="reddit-thread"),
    ]
    clusters = cluster_complaints(c, threshold=0.5)
    # Expect roughly 2 clusters: mobile/crash, pricing
    assert 2 <= len(clusters) <= 3
    sizes = sorted(len(g) for g in clusters)
    assert sizes[-1] >= 2
