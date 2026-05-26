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

from wedge.types import Complaint

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
