import pytest
from quantqueue.execution.retry import retry_async

@pytest.mark.asyncio
async def test_retry_async_invalid_attempts():
    async def dummy():
        return 42

    with pytest.raises(ValueError, match="attempts must be at least 1"):
        await retry_async(dummy, attempts=0)

@pytest.mark.asyncio
async def test_retry_async_retries_transient_error():
    calls = 0

    async def transient_operation():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ConnectionError("Temporary connection failure")
        return "success"

    result = await retry_async(transient_operation, attempts=3, base_delay=0.001)
    assert result == "success"
    assert calls == 3

@pytest.mark.asyncio
async def test_retry_async_exhausts_retries():
    calls = 0

    async def always_fails():
        nonlocal calls
        calls += 1
        raise TimeoutError("Timed out")

    with pytest.raises(TimeoutError):
        await retry_async(always_fails, attempts=2, base_delay=0.001)
    assert calls == 2
