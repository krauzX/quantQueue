from quantqueue.cache import TranspilationCache

def test_cache_round_trip(tmp_path):
    cache = TranspilationCache(tmp_path)
    key = cache.make_key({"qubits": 2}, {"backend": "mock"})
    assert cache.get(key) is None
    cache.set(key, {"counts": {"00": 10}})
    assert cache.get(key) == {"counts": {"00": 10}}

def test_key_changes_with_config():
    a = TranspilationCache.make_key({"qubits": 2}, {"basis": ["x"]})
    b = TranspilationCache.make_key({"qubits": 2}, {"basis": ["h"]})
    assert a != b
