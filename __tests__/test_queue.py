import pytest
from quantqueue import Job, QuantQueue

@pytest.mark.asyncio
async def test_queue_executes_jobs(tmp_path):
    queue = QuantQueue(workers=2, cache_dir=tmp_path, use_cache=False)
    await queue.start()
    ids = [await queue.submit(Job({"qubits": 3, "seed": i})) for i in range(4)]
    results = [await queue.get_result(i, timeout=2) for i in ids]
    await queue.close()
    assert all(r.status == "success" for r in results)
    assert all(r.output["backend"] == "mock" for r in results)
