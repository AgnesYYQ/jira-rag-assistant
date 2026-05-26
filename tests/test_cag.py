from jirabot.cag import CAG

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
