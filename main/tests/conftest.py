from time import monotonic
import numpy as np
import pytest
from beatlight.contracts import AudioBlock


@pytest.fixture
def block_factory():
    def make(samples, sequence=0, rate=48000, discontinuity=False):
        x = np.asarray(samples, dtype=np.float32)
        if x.ndim == 1:
            x = x[:, None]
        x.setflags(write=False)
        now = monotonic()
        return AudioBlock("test", x, rate, x.shape[1], sequence, len(x),
                          now - len(x) / rate, now, discontinuity)
    return make
