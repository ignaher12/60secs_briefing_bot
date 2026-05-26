"""Synthesis: cluster complaints into thematic groups.

Uses scikit-learn's TF-IDF + agglomerative clustering as a pragmatic
stand-in for embeddings — fast, deterministic, no extra API calls.

A small suffix-stripping stemmer is applied so that morphological
variants (``crashes``/``crashing``, ``pricing``/``prices``) collapse to
the same token before vectorization.
"""

from __future__ import annotations

import re

from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer

from wedge.types import Brief, Competitor, Complaint, ComplaintTheme

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "has", "have", "he", "i", "in", "is", "it", "its", "of", "on", "or",
    "she", "so", "that", "the", "they", "this", "to", "too", "us", "was",
    "we", "were", "will", "with", "you", "your", "their", "them", "out",
    "keeps", "kept", "keep",
}


def _stem(word: str) -> str:
    """Very small suffix stripper — good enough for short complaint snippets."""
    for suf in ("ings", "ing", "ies", "ied", "ed", "es", "s"):
        if word.endswith(suf) and len(word) > len(suf) + 2:
            return word[: -len(suf)]
    return word


def _analyze(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    return [_stem(t) for t in tokens if len(t) > 2 and t not in _STOPWORDS]


def cluster_complaints(
    complaints: list[Complaint], *, threshold: float = 0.6
) -> list[list[Complaint]]:
    """Group complaints by textual similarity.

    Args:
        complaints: list of Complaint objects.
        threshold: cosine-distance cut-off for agglomerative clustering.
            Pairs with distance <= threshold may be merged.

    Returns:
        A list of clusters; each cluster is a list of Complaints.
    """
    if len(complaints) <= 1:
        return [complaints] if complaints else []

    texts = [c.excerpt for c in complaints]
    vec = TfidfVectorizer(
        analyzer=_analyze,
        ngram_range=(1, 1),
        min_df=1,
        use_idf=False,
        sublinear_tf=True,
        norm="l2",
    )
    X = vec.fit_transform(texts).toarray()

    clust = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",
        linkage="average",
        distance_threshold=threshold,
    )
    labels = clust.fit_predict(X)

    groups: dict[int, list[Complaint]] = {}
    for label, complaint in zip(labels, complaints):
        groups.setdefault(int(label), []).append(complaint)
    return list(groups.values())


SYSTEM = """You write a Market Opportunity Brief from clustered customer complaints.
Return ONLY JSON:
{
  "tldr": string,
  "themes": [
    {"label": string, "frequency": int, "severity": "low"|"medium"|"high",
     "sample_quotes": [string,...], "competitors_affected": [string,...]}
  ],
  "gaps": [string,...],
  "positioning": [string,...]
}"""


def _format_clusters_for_llm(clusters: list[list[Complaint]]) -> str:
    lines = []
    for i, group in enumerate(clusters):
        competitors = sorted({c.competitor for c in group})
        lines.append(
            f"Cluster {i+1} ({len(group)} complaints, competitors: {competitors}):"
        )
        for c in group[:6]:
            lines.append(f"  - [{c.source} | {c.competitor}] {c.excerpt}")
    return "\n".join(lines)


def synthesize(
    *,
    idea: str,
    competitors: list[Competitor],
    complaints: list[Complaint],
    llm=None,
    partial: bool = False,
) -> Brief:
    """Cluster complaints and ask the LLM to synthesize a Market Opportunity Brief."""
    from wedge.llm import LLMClient

    llm = llm or LLMClient()
    # Looser threshold than the clustering default (0.6): real-world stemmed
    # TF-IDF distances on short complaint excerpts run tighter than the plan
    # assumed, so we widen the cut-off to merge thematically related pairs.
    clusters = cluster_complaints(complaints, threshold=0.75)
    user = (
        f"Idea: {idea}\n"
        f"Competitors: {[c.name for c in competitors]}\n\n"
        f"{_format_clusters_for_llm(clusters)}"
    )
    data = llm.call_json(model="sonnet", system=SYSTEM, user=user, max_tokens=4096)
    themes = [
        ComplaintTheme(
            label=t["label"],
            frequency=int(t["frequency"]),
            severity=t["severity"],
            sample_quotes=t.get("sample_quotes", []),
            competitors_affected=t.get("competitors_affected", []),
        )
        for t in data.get("themes", [])
    ]
    return Brief(
        idea=idea,
        tldr=data.get("tldr", ""),
        competitor_table=competitors,
        themes=themes,
        gaps=data.get("gaps", []),
        positioning=data.get("positioning", []),
        partial=partial,
    )
