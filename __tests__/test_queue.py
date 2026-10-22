import asyncio
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

@pytest.mark.asyncio
async def test_submit_to_closed_queue_raises(tmp_path):
    queue = QuantQueue(workers=1, cache_dir=tmp_path, use_cache=False)
    await queue.start()
    await queue.close()
    with pytest.raises(RuntimeError, match="queue is closed"):
        await queue.submit(Job({"qubits": 1}))

def test_invalid_worker_count_raises(tmp_path):
    with pytest.raises(ValueError, match="workers must be at least 1"):
        QuantQueue(workers=0, cache_dir=tmp_path)

@pytest.mark.asyncio
async def test_get_result_timeout(tmp_path):
    queue = QuantQueue(workers=1, cache_dir=tmp_path, use_cache=False)
    await queue.start()
    with pytest.raises((asyncio.TimeoutError, TimeoutError)):
        await queue.get_result("non_existent_job_id", timeout=0.01)
    await queue.close()

@pytest.mark.asyncio
async def test_job_failure_handling(tmp_path):
    queue = QuantQueue(workers=1, cache_dir=tmp_path, use_cache=False, retry_attempts=1)

    class FailingExecutor:
        async def run(self, payload):
            raise RuntimeError("Simulated execution failure")

    queue.executor = FailingExecutor()
    await queue.start()
    job_id = await queue.submit(Job({"qubits": 1}))
    result = await queue.get_result(job_id, timeout=2)
    await queue.close()
    assert result.status == "failed"
    assert "Simulated execution failure" in (result.error or "")

