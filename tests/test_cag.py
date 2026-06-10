from jirabot.cag import CAG


# ---------------------------------------------------------------------------
# Exact-match tests
# ---------------------------------------------------------------------------

def test_cag_set_get():
    cache = CAG()
    cache.set('foo', 'bar')
    assert cache.get('foo') == 'bar'


def test_cag_default():
    cache = CAG()
    assert cache.get('missing', 42) == 42


def test_cag_delete():
    cache = CAG()
    cache.set('foo', 'bar')
    cache.delete('foo')
    assert cache.get('foo') is None


def test_cag_clear():
    cache = CAG()
    cache.set('a', 1)
    cache.set('b', 2)
    cache.clear()
    assert cache.get('a') is None
    assert cache.get('b') is None


def test_cag_overwrite():
    cache = CAG()
    cache.set('key', 'old')
    cache.set('key', 'new')
    assert cache.get('key') == 'new'


def test_cag_contains():
    cache = CAG()
    cache.set('hello', 'world')
    assert 'hello' in cache
    assert 'missing' not in cache


def test_cag_len():
    cache = CAG()
    assert len(cache) == 0
    cache.set('a', 1)
    cache.set('b', 2)
    assert len(cache) == 2


# ---------------------------------------------------------------------------
# Semantic-cache tests
# ---------------------------------------------------------------------------

def test_semantic_similar_query_hits():
    """Semantically similar queries should return the same cached result."""
    cache = CAG(similarity_threshold=0.70)
    cache.set("How do I reset my password?", "Reset instructions")

    # Paraphrase — should trigger semantic hit
    result = cache.get("How can I reset my password?")
    assert result == "Reset instructions", f"Expected 'Reset instructions', got {result!r}"


def test_semantic_dissimilar_query_misses():
    """Queries with different meaning should NOT trigger a semantic hit."""
    cache = CAG(similarity_threshold=0.80)
    cache.set("How do I reset my password?", "Reset instructions")

    result = cache.get("What is the weather today?")
    assert result is None, "Unrelated query should not match"


def test_semantic_stats():
    """Cache stats should differentiate exact hits from semantic hits."""
    cache = CAG(similarity_threshold=0.70)
    cache.set("reset password", "instructions")

    # Exact hit
    cache.get("reset password")
    assert cache.stats["exact_hits"] == 1
    assert cache.stats["semantic_hits"] == 0

    # Semantic hit
    cache.get("how to reset my password")
    assert cache.stats["semantic_hits"] == 1

    # Miss
    cache.get("what is the weather")
    assert cache.stats["misses"] == 1
    assert cache.stats["hit_rate"] > 0


def test_semantic_threshold_setter():
    cache = CAG(similarity_threshold=0.99)
    assert cache.similarity_threshold == 0.99
    cache.similarity_threshold = 0.75
    assert cache.similarity_threshold == 0.75
