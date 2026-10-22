from quantqueue.scheduler import Scheduler
from quantqueue import Job

def test_fifo_order():
    scheduler = Scheduler("fifo")
    first, second = Job({}), Job({})
    scheduler.put(first); scheduler.put(second)
    assert scheduler.get() is first
    assert scheduler.get() is second

def test_priority_order():
    scheduler = Scheduler("priority")
    low, high = Job({}, urgency=1), Job({}, urgency=5)
    scheduler.put(low); scheduler.put(high)
    assert scheduler.get() is high
