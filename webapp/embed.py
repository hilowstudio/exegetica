"""Shared static-embedding encoder for in-memory semantic retrieval.

Same model the standards search uses (model2vec `potion-retrieval-32M`): CPU-only, no API, loaded
lazily from the baked HF cache (HF_HUB_OFFLINE=1). Used by the Living Library generator to pick the
most relevant passages within a large covered range when the whole range won't fit in context.
"""
from __future__ import annotations

import numpy as np

_MODEL = None


def _model():
    global _MODEL
    if _MODEL is None:
        from model2vec import StaticModel
        _MODEL = StaticModel.from_pretrained("minishlab/potion-retrieval-32M")
    return _MODEL


def encode(texts: list[str]) -> np.ndarray:
    """L2-normalized embeddings (so a dot product is cosine similarity)."""
    v = np.asarray(_model().encode(list(texts)), dtype="float32")
    n = np.linalg.norm(v, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return v / n


def topk(query: str, passages: list[str], k: int) -> list[tuple[int, float]]:
    """Return up to k (index, cosine-score) pairs for the passages most relevant to `query`,
    ranked high→low. Empty list if there are no passages."""
    if not passages:
        return []
    pv = encode(passages)
    qv = encode([query])[0]
    scores = pv @ qv
    order = np.argsort(-scores)[: max(0, k)]
    return [(int(i), float(scores[i])) for i in order]
