"""
CAG (Cache, k, v) module for simple key-value caching.
"""

class CAG:
    def __init__(self):
        self._cache = {}

    def set(self, k, v):
        self._cache[k] = v

    def get(self, k, default=None):
        return self._cache.get(k, default)

    def delete(self, k):
        if k in self._cache:
            del self._cache[k]

    def clear(self):
        self._cache.clear()
