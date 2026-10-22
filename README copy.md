# QuantQueue

An asynchronous scheduler for quantum-circuit workloads, with priority scheduling, transpilation caching, retries, and a small CLI.

> **Status:** starter implementation. Benchmark figures in the original proposal were illustrative, not measured results. Run `python runner.py --benchmark` to measure your own environment.

## Features
- Async producer/consumer queue with FIFO and priority policies.
- Priority score based on urgency, estimated depth, and qubit width.
- Optional Qiskit/Aer execution adapter; a deterministic mock backend works without Qiskit.
- SHA-256 cache keys for serialized circuit representations and backend settings.
- Retry with exponential backoff for configured transient failures.
- CLI workload generator and benchmark mode.

## Install

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

For Qiskit execution, install the optional extras:

```bash
pip install -e '.[qiskit]'
```

## Quick start

```bash
python runner.py --workload random --circuits 20 --workers 4 --mode priority
python runner.py --workload random --circuits 100 --workers 8 --mode fifo --cache warm
python runner.py --benchmark
```

The default workload uses mock circuits so it can run without quantum packages. `--backend aer` requests Qiskit Aer and requires the optional dependencies.

## Python API

```python
import asyncio
from quantqueue import QuantQueue, Job

async def main():
    queue = QuantQueue(workers=4, mode="priority")
    await queue.start()
    job_id = await queue.submit(Job(payload={"name": "demo", "qubits": 4},
                                    urgency=2.0))
    result = await queue.get_result(job_id)
    print(result.status, result.output)
    await queue.close()

asyncio.run(main())
```

## Project layout

- `quantqueue/queue_core.py` — async queue, workers, result tracking
- `quantqueue/scheduler.py` — FIFO and priority policies
- `quantqueue/cache.py` — disk-backed JSON cache and SHA-256 keys
- `quantqueue/execution/` — mock/Aer execution and retry helper
- `benchmarks/benchmark.py` — basic throughput/latency benchmark
- `runner.py` — command-line entry point
- `tests/` — unit tests

## Notes
- Priority scheduling changes ordering, not the guarantees of a real QPU provider.
- The starter cache stores JSON-compatible transpilation outputs. Provider-specific circuit serialization may need a custom serializer.
- A successful local mock run does not imply performance or reliability on a cloud QPU.
