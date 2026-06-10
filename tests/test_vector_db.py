import os
import pytest
from jirabot.vector_db import VectorDB

KB_PATH = os.path.join(os.path.dirname(__file__), '../kb_data/sample_kb.json')


def test_vector_db_query():
    db = VectorDB(KB_PATH)
    results = db.query('reset password', top_k=2)
    assert any('password' in r['question'] for r in results)
    results = db.query('create issue', top_k=2)
    assert any('create' in r['question'] for r in results)
    results = db.query('assign', top_k=2)
    assert any('assign' in r['question'] for r in results)


# ---------------------------------------------------------------------------
# VectorDB cache integration tests
# ---------------------------------------------------------------------------

def test_vector_db_cache_exact_hit():
    db = VectorDB(KB_PATH)

    # First call populates the cache (uses _CACHE_MAX_K results internally)
    r1 = db.query('reset password', top_k=2)
    assert db.cache_stats["exact_hits"] == 0  # not cached yet
    assert db.cache_stats["misses"] == 1
    assert len(r1) == 2

    # Second call with identical text — should be an exact hit
    r2 = db.query('reset password', top_k=2)
    assert db.cache_stats["exact_hits"] == 1
    # Same underlying dict objects (the slice creates a new list but shares
    # the dict references)
    assert len(r1) == len(r2)
    for a, b in zip(r1, r2):
        assert a is b


def test_vector_db_cache_different_top_k_reuses_cache():
    """Query with same text but different top_k reuses cached full result set."""
    db = VectorDB(KB_PATH)

    r1 = db.query('reset password', top_k=1)
    db_stats = dict(db.cache_stats)

    r2 = db.query('reset password', top_k=5)
    # Second call should be an exact hit (same text key)
    assert db.cache_stats["exact_hits"] == 1
    # r1 and r2 share the same underlying list, r2 just gets a longer slice
    assert r1 is r2 or r1[0] is r2[0]  # same cached objects
    assert len(r2) >= len(r1)


def test_vector_db_cache_semantic_hit():
    db = VectorDB(KB_PATH, cache_threshold=0.60)

    # Prime cache with one query
    db.query('how to reset my password', top_k=2)

    # Similar paraphrase — should trigger semantic hit
    r2 = db.query('how do I reset my password', top_k=2)
    assert db.cache_stats["semantic_hits"] >= 1
    assert len(r2) > 0


def test_vector_db_cache_bypass():
    db = VectorDB(KB_PATH)

    r1 = db.query('reset password', top_k=2)
    stats_before = dict(db.cache_stats)

    # Bypass cache with use_cache=False
    r2 = db.query('reset password', top_k=2, use_cache=False)
    # stats should be unchanged (no new hits or misses recorded)
    assert db.cache_stats == stats_before


def test_vector_db_cache_clear():
    db = VectorDB(KB_PATH)

    db.query('reset password', top_k=2)
    assert db.cache_stats["size"] > 0

    db.clear_cache()
    assert db.cache_stats["size"] == 0
