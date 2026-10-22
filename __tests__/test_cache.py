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

def test_corrupted_cache_file_returns_none(tmp_path):
    cache = TranspilationCache(tmp_path)
    corrupted_file = tmp_path / "corrupted_key.json"
    corrupted_file.write_text("{this is not valid json", encoding="utf-8")
    assert cache.get("corrupted_key") is None

