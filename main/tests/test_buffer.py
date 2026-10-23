import numpy as np
from beatlight.streams.buffer import RecentBlockQueue


def test_overload_discards_oldest_and_reports_loss(block_factory):
    queue = RecentBlockQueue(2)
    for seq in range(3):
        queue.put(block_factory(np.zeros((16, 2)), sequence=seq))
    assert queue.metrics() == (1, 2)
    assert queue.get().sequence == 1
    assert queue.get().sequence == 2
    assert queue.get(timeout=0.001) is None
    queue.reset()
    assert queue.metrics() == (0, 0)
