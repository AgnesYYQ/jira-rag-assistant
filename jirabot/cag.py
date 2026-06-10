"""
CAG (Cache, Augmented Generation) module with two-tier caching:

1. **Exact-match cache** — Fast dict lookup for repeated identical queries.
2. **Semantic cache** — Embedding-based similarity lookup for queries that are
   semantically equivalent but not byte-identical.

Uses the same sentence-transformers model as VectorDB so no extra dependencies.
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-D vectors."""
    dot = float(np.dot(a, b))
    norm = float(np.linalg.norm(a)) * float(np.linalg.norm(b))
    return dot / norm if norm > 0 else 0.0


# ---------------------------------------------------------------------------
# Cache entry
# ---------------------------------------------------------------------------

class _CacheEntry:
    """Internal wrapper around a cached value."""

    __slots__ = ("value", "embedding", "hit_count")

    def __init__(self, value, embedding: np.ndarray):
        self.value = value
        self.embedding = embedding
        self.hit_count = 0


# ---------------------------------------------------------------------------
# CAG
# ---------------------------------------------------------------------------

class CAG:
    """Two-tier cache: exact-match (fast) + semantic (embedding-based).

    Parameters
    ----------
    model_name:
        Sentence-transformer model for computing query embeddings.
    similarity_threshold:
        Minimum cosine similarity (0..1) for a semantic cache hit.
        Higher values = stricter matching.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.85,
    ):
        self._threshold = similarity_threshold
        self._model = SentenceTransformer(model_name)
        self._exact: dict[str, _CacheEntry] = {}  # key → entry
        self._embeddings: list[np.ndarray] = []    # parallel list for O(n) scan
        self._keys: list[str] = []                  # parallel list for O(n) scan

        # Stats
        self._exact_hits = 0
        self._semantic_hits = 0
        self._misses = 0

    # -- public API ---------------------------------------------------------

    def set(self, k: str, v, semantic_key: str | None = None):
        """Store *v* under key *k*.

        Parameters
        ----------
        k:
            Exact-match lookup key.
        v:
            Value to cache.
        semantic_key:
            Text used for embedding computation (for semantic lookups).
            Defaults to *k* itself.  Use this when *k* contains auxiliary
            suffixes (e.g. ``"query__top_k=5"``) that would pollute the
            embedding.
        """
        embed_text = semantic_key or k
        emb = self._model.encode([embed_text], normalize_embeddings=True)[0]
        entry = _CacheEntry(value=v, embedding=emb)
        # Update exact match
        if k in self._exact:
            # Replace in-place so existing references stay valid
            old = self._exact[k]
            idx = self._keys.index(k)
            self._embeddings[idx] = emb
            old.value = v
            old.embedding = emb
        else:
            self._exact[k] = entry
            self._embeddings.append(emb)
            self._keys.append(k)

    def get(self, k: str, default=None, semantic_key: str | None = None):
        """Retrieve cached value for key *k*.

        Tries exact match first (using *k*), then falls back to semantic
        similarity (using *semantic_key* or *k*).

        Parameters
        ----------
        k:
            Exact-match lookup key.
        default:
            Value returned when nothing matches.
        semantic_key:
            Text used for the embedding query during semantic lookup.
            Defaults to *k* itself.  Use this when *k* contains auxiliary
            suffixes that shouldn't affect the semantic comparison.
        """
        # 1. Exact match — O(1)
        entry = self._exact.get(k)
        if entry is not None:
            entry.hit_count += 1
            self._exact_hits += 1
            return entry.value

        # 2. Semantic match — O(n) scan
        if self._embeddings:
            query_emb = self._model.encode(
                [semantic_key or k], normalize_embeddings=True
            )[0]
            best_sim = -1.0
            best_idx = -1
            for idx, stored_emb in enumerate(self._embeddings):
                sim = _cosine_similarity(query_emb, stored_emb)
                if sim > best_sim:
                    best_sim = sim
                    best_idx = idx

            if best_sim >= self._threshold and best_idx >= 0:
                key = self._keys[best_idx]
                entry = self._exact[key]
                entry.hit_count += 1
                self._semantic_hits += 1
                return entry.value

        # 3. Miss
        self._misses += 1
        return default

    def delete(self, k: str):
        """Remove entry for key *k* (if present)."""
        if k in self._exact:
            idx = self._keys.index(k)
            del self._exact[k]
            del self._embeddings[idx]
            del self._keys[idx]

    def clear(self):
        """Drop all cached entries and reset stats."""
        self._exact.clear()
        self._embeddings.clear()
        self._keys.clear()
        self._exact_hits = 0
        self._semantic_hits = 0
        self._misses = 0

    def __contains__(self, k: str) -> bool:
        return k in self._exact

    def __len__(self) -> int:
        return len(self._exact)

    # -- statistics ---------------------------------------------------------

    @property
    def stats(self) -> dict:
        """Summary of cache performance."""
        total = self._exact_hits + self._semantic_hits + self._misses
        return {
            "size": len(self._exact),
            "exact_hits": self._exact_hits,
            "semantic_hits": self._semantic_hits,
            "misses": self._misses,
            "hit_rate": round((self._exact_hits + self._semantic_hits) / max(1, total), 3),
        }

    @property
    def similarity_threshold(self) -> float:
        return self._threshold

    @similarity_threshold.setter
    def similarity_threshold(self, value: float):
        self._threshold = value
