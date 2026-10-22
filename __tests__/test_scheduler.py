import pytest
from quantqueue import Job
from quantqueue.scheduler import Scheduler

def test_fifo_order():
    scheduler = Scheduler("fifo")
    first, second = Job({}), Job({})
    scheduler.put(first)
    scheduler.put(second)
    assert scheduler.get() is first
    assert scheduler.get() is second

def test_priority_order():
    scheduler = Scheduler("priority")
    low, high = Job({}, urgency=1), Job({}, urgency=5)
    scheduler.put(low)
    scheduler.put(high)
    assert scheduler.get() is high

def test_invalid_scheduler_mode_raises():
    with pytest.raises(ValueError, match="mode must be 'fifo' or 'priority'"):
        Scheduler("invalid")

def test_empty_scheduler_get_returns_none():
    scheduler = Scheduler("fifo")
    assert len(scheduler) == 0
    assert scheduler.get() is None

