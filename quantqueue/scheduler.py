from __future__ import annotations
import heapq
import itertools
from dataclasses import dataclass, field
from typing import Any

@dataclass(order=True)
class QueueEntry:
    sort_key: tuple[float, int]
    job: Any = field(compare=False)

class Scheduler:
    """Small scheduling heap. FIFO preserves insertion order; priority favors urgency."""
    def __init__(self, mode: str = "priority"):
        if mode not in {"fifo", "priority"}:
            raise ValueError("mode must be 'fifo' or 'priority'")
        self.mode = mode
        self._heap: list[QueueEntry] = []
        self._counter = itertools.count()

    def put(self, job: Any) -> None:
        sequence = next(self._counter)
        if self.mode == "fifo":
            key = (0.0, sequence)
        else:
            # Lower key is dequeued first. Higher urgency wins; estimated cost breaks ties.
            score = -(float(job.urgency) * 1000.0) + float(job.estimated_depth) + float(job.qubits) * 0.1
            key = (score, sequence)
        heapq.heappush(self._heap, QueueEntry(key, job))

    def get(self):
        return heapq.heappop(self._heap).job if self._heap else None

    def __len__(self) -> int:
        return len(self._heap)
