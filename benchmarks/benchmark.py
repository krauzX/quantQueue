from __future__ import annotations
import asyncio
import time
from quantqueue import Job, QuantQueue

async def run_benchmark(circuits: int = 100, workers: int = 4, mode: str = "priority"):
    queue = QuantQueue(workers=workers, mode=mode, use_cache=False)
    await queue.start()
    start = time.perf_counter()
    ids = [await queue.submit(Job(payload={"qubits": 16, "seed": i},
                                  urgency=float((i % 5) + 1),
                                  estimated_depth=float((i % 20) + 1), qubits=16))
           for i in range(circuits)]
    results = [await queue.get_result(job_id) for job_id in ids]
    elapsed = time.perf_counter() - start
    await queue.close()
    latencies = sorted(r.queue_latency_ms for r in results)
    successful = sum(r.status == "success" for r in results)
    return {"jobs": circuits, "workers": workers, "mode": mode,
            "elapsed_seconds": round(elapsed, 4),
            "throughput_jobs_per_sec": round(circuits / elapsed, 2) if elapsed else 0,
            "mean_queue_latency_ms": round(sum(latencies) / len(latencies), 3) if latencies else 0,
            "success_rate_percent": round(successful / circuits * 100, 2) if circuits else 100}

def main():
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument("--circuits", type=int, default=100)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--mode", choices=["fifo", "priority"], default="priority")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run_benchmark(args.circuits, args.workers, args.mode)), indent=2))

if __name__ == "__main__":
    main()
