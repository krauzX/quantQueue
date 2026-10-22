from __future__ import annotations
import argparse
import asyncio
import json
import random
from quantqueue import Job, QuantQueue
from benchmarks.benchmark import run_benchmark

async def run(args):
    if args.benchmark:
        print(json.dumps(await run_benchmark(args.circuits, args.workers, args.mode), indent=2))
        return
    queue = QuantQueue(workers=args.workers, mode=args.mode, backend=args.backend,
                       use_cache=args.cache != "off")
    await queue.start()
    rng = random.Random(args.seed)
    ids = []
    for i in range(args.circuits):
        payload = {"qubits": rng.randint(2, 16), "shots": args.shots, "seed": i}
        ids.append(await queue.submit(Job(payload=payload,
            urgency=float(rng.randint(1, 5)), estimated_depth=float(rng.randint(1, 100)),
            qubits=payload["qubits"])))
    results = [await queue.get_result(job_id) for job_id in ids]
    await queue.close()
    summary = {"submitted": len(results), "successful": sum(r.status == "success" for r in results),
               "failed": sum(r.status == "failed" for r in results),
               "mean_queue_latency_ms": round(sum(r.queue_latency_ms for r in results)/len(results), 3) if results else 0,
               "results": [{"job_id": r.job_id, "status": r.status, "output": r.output, "error": r.error}
                           for r in results]}
    print(json.dumps(summary, indent=2, default=str))

def main():
    parser = argparse.ArgumentParser(description="QuantQueue quantum workload scheduler")
    parser.add_argument("--workload", choices=["random", "vqe"], default="random",
                        help="vqe currently maps to a parameter-sweep-style mock workload")
    parser.add_argument("--circuits", type=int, default=20)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--mode", choices=["fifo", "priority"], default="priority")
    parser.add_argument("--cache", choices=["off", "cold", "warm"], default="cold")
    parser.add_argument("--backend", choices=["mock", "aer"], default="mock")
    parser.add_argument("--shots", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--benchmark", action="store_true")
    args = parser.parse_args()
    if args.circuits < 0 or args.workers < 1 or args.shots < 1:
        parser.error("circuits must be >= 0, workers and shots must be >= 1")
    asyncio.run(run(args))

if __name__ == "__main__":
    main()
