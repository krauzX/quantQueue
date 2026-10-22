from __future__ import annotations
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any
from .scheduler import Scheduler
from .cache import TranspilationCache
from .execution.executor import MockExecutor, AerExecutor
from .execution.retry import retry_async

@dataclass
class Job:
    payload: dict[str, Any]
    urgency: float = 1.0
    estimated_depth: float = 1.0
    qubits: int = 1
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class JobResult:
    job_id: str
    status: str
    output: Any = None
    error: str | None = None
    queue_latency_ms: float = 0.0
    execution_time_ms: float = 0.0

class QuantQueue:
    def __init__(self, workers: int = 4, mode: str = "priority",
                 backend: str = "mock", cache_dir: str = ".quantqueue-cache",
                 use_cache: bool = True, retry_attempts: int = 3):
        if workers < 1:
            raise ValueError("workers must be at least 1")
        self.workers = workers
        self.scheduler = Scheduler(mode)
        self.executor = AerExecutor() if backend == "aer" else MockExecutor()
        self.cache = TranspilationCache(cache_dir)
        self.use_cache = use_cache
        self.retry_attempts = retry_attempts
        self._condition = asyncio.Condition()
        self._tasks: list[asyncio.Task] = []
        self._results: dict[str, JobResult] = {}
        self._submitted_at: dict[str, float] = {}
        self._closed = False

    async def start(self) -> None:
        if self._tasks:
            return
        self._closed = False
        self._tasks = [asyncio.create_task(self._worker(), name=f"quantqueue-worker-{i}")
                       for i in range(self.workers)]

    async def submit(self, job: Job) -> str:
        if self._closed:
            raise RuntimeError("queue is closed")
        if not self._tasks:
            await self.start()
        self._submitted_at[job.job_id] = time.perf_counter()
        async with self._condition:
            self.scheduler.put(job)
            self._condition.notify()
        return job.job_id

    async def get_result(self, job_id: str, timeout: float | None = None) -> JobResult:
        async def wait():
            while job_id not in self._results:
                await asyncio.sleep(0.005)
            return self._results[job_id]
        return await asyncio.wait_for(wait(), timeout) if timeout is not None else await wait()

    async def _next_job(self):
        async with self._condition:
            while not len(self.scheduler) and not self._closed:
                await self._condition.wait()
            return self.scheduler.get()

    async def _worker(self):
        while True:
            job = await self._next_job()
            if job is None:
                if self._closed:
                    return
                continue
            started = time.perf_counter()
            queued = (started - self._submitted_at.get(job.job_id, started)) * 1000
            cache_key = self.cache.make_key(job.payload, {"backend": type(self.executor).__name__})
            try:
                cached = self.cache.get(cache_key) if self.use_cache else None
                if cached is not None:
                    output = cached
                else:
                    output = await retry_async(lambda: self.executor.run(job.payload),
                                               attempts=self.retry_attempts)
                    if self.use_cache:
                        self.cache.set(cache_key, output)
                self._results[job.job_id] = JobResult(job.job_id, "success", output,
                    queue_latency_ms=queued, execution_time_ms=(time.perf_counter()-started)*1000)
            except Exception as exc:
                self._results[job.job_id] = JobResult(job.job_id, "failed", error=f"{type(exc).__name__}: {exc}",
                    queue_latency_ms=queued, execution_time_ms=(time.perf_counter()-started)*1000)

    async def close(self) -> None:
        self._closed = True
        async with self._condition:
            self._condition.notify_all()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
