"""
VectorDB: Simple vector database using FAISS and sentence-transformers,
with two-tier CAG caching (exact + semantic).
"""
import faiss
from sentence_transformers import SentenceTransformer
import numpy as np
import json
import os
from jirabot.cag import CAG
from jirabot.query_scoring import (
    confidence_from_distance,
    complexity_from_text,
    format_citation,
    format_citation_markdown,
)

class VectorDB:
    def __init__(self, kb_path, model_name='all-MiniLM-L6-v2', cache_threshold=0.85):
        self.kb_path = kb_path
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.data = []
        self.embeddings = None
        # Two-tier cache: exact-match + semantic (embedding-based)
        self._cache = CAG(model_name=model_name, similarity_threshold=cache_threshold)
        self._load_kb()

    def _load_kb(self):
        import re
        import datetime
        if not os.path.exists(self.kb_path):
            raise FileNotFoundError(f"KB file not found: {self.kb_path}")
        with open(self.kb_path, 'r') as f:
            raw_data = json.load(f)
        filtered = []
        now = datetime.datetime.utcnow()
        one_year_ago = now - datetime.timedelta(days=365)
        for item in raw_data:
            # Filter out obsolete wiki/code entries
            if any(
                re.search(r"obsolete", str(item.get(field, "")), re.IGNORECASE)
                for field in ["question", "answer", "folder", "wiki_title"]
            ):
                continue
            # Only keep Jira issues that are Closed/Solved
            if item.get("type") == "jira_issue":
                if item.get("status") != "Closed" or item.get("resolution") != "Solved":
                    continue
            # Filter out old Jira issues (if date field exists)
            date_str = item.get("created") or item.get("date")
            if date_str:
                try:
                    dt = datetime.datetime.fromisoformat(date_str)
                    if dt < one_year_ago:
                        continue
                except Exception:
                    pass
            filtered.append(item)
        self.data = filtered
        questions = [item['question'] for item in self.data]
        if questions:
            self.embeddings = self.model.encode(questions, convert_to_numpy=True)
            self.index = faiss.IndexFlatL2(self.embeddings.shape[1])
            self.index.add(self.embeddings)
        else:
            self.embeddings = None
            self.index = None

    # Maximum number of results to cache per query.  When a query with a
    # smaller *top_k* hits a semantically-cached entry that stored *max_k*
    # results, the extra ones are simply sliced off.
    _CACHE_MAX_K = 20

    def query(self, text, top_k=3, use_cache=True):
        """Search the vector DB, with optional two-tier caching.

        When *use_cache* is ``True`` (default), the query first checks a
        two-tier cache:
          - **exact match** — fast dict lookup for repeated identical queries.
          - **semantic match** — embedding similarity for paraphrased queries.

        On a cache miss the normal FAISS search runs and the result is
        automatically stored for future lookups under a generous ``top_k``
        so that subsequent calls with smaller (or equal) ``top_k`` values
        can reuse the cached data.
        """
        # ---- Cache check (exact → semantic) ----
        if use_cache:
            cached = self._cache.get(text, semantic_key=text)
            if cached is not None:
                return cached[:top_k]  # slice to desired count

        # ---- Normal FAISS search (at max_k to maximise cache reuse) ----
        max_k = max(top_k, self._CACHE_MAX_K)
        query_vec = self.model.encode([text], convert_to_numpy=True)
        D, I = self.index.search(query_vec, max_k)
        results = []
        for position, idx in enumerate(I[0]):
            if idx < len(self.data):
                item = dict(self.data[idx])
                distance = float(D[0][position]) if position < len(D[0]) else None
                confidence_score = confidence_from_distance(distance)
                complexity_score, complexity_label = complexity_from_text(
                    f"{item.get('question', '')}\n{item.get('answer', '')}"
                )
                item["distance"] = distance
                # Cosine similarity between the query and this result's embedding
                if self.embeddings is not None and idx < len(self.embeddings):
                    a = query_vec[0]
                    b = self.embeddings[idx]
                    dot = float(np.dot(a, b))
                    norm = float(np.linalg.norm(a)) * float(np.linalg.norm(b))
                    item["cosine_similarity"] = round(dot / norm, 4) if norm > 0 else 0.0
                else:
                    item["cosine_similarity"] = None
                item["confidence_score"] = confidence_score
                item["complexity_score"] = complexity_score
                item["complexity_label"] = complexity_label
                # Citation / Attribution
                item["citation"] = format_citation(item)
                item["citation_markdown"] = format_citation_markdown(item)
                results.append(item)

        # ---- Store in cache (the full result set) ----
        if use_cache:
            self._cache.set(text, results, semantic_key=text)

        return results[:top_k]

    def clear_cache(self):
        """Drop all cached query results."""
        self._cache.clear()

    @property
    def cache_stats(self) -> dict:
        """Cache performance counters (exact hits, semantic hits, misses …)."""
        return self._cache.stats
