import numpy as np
import pytest
from beatlight.contracts import AudioBlock
from beatlight.dsp.structure_features import StructureFeatureExtractor


def extract(rate, frequency):
    extractor = StructureFeatureExtractor()
    frames = []
    for sequence, first in enumerate(range(0, 48000 * 3, 512)):
        t = np.arange(first, first + 512) / 48000
        envelope = np.exp(-((t * rate) % 1) * 14)
        x = (0.45 * envelope * np.sin(2 * np.pi * frequency * t)
             + 0.02 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)[:, None]
        x.setflags(write=False)
        frames.extend(extractor.push(AudioBlock("roll", x, 48000, 1, sequence, 512, 100 + first / 48000, 100 + (first + 512) / 48000)))
    return [f for f in frames if f.at > 101]


@pytest.mark.parametrize("rate", [8, 16])
def test_snare_like_rolls_keep_temporal_attacks_even_at_sixteenth_subdivisions(rate):
    frames = extract(rate, 1400)
    times = [f.at for f in frames if f.percussion_onset]
    assert rate * 2 * 0.7 <= len(times) <= rate * 2 * 1.3
    assert all(b - a >= 0.04 for a, b in zip(times, times[1:]))


def test_high_hats_do_not_supply_midrange_roll_evidence():
    frames = extract(8, 8000)
    assert sum(f.onset for f in frames) >= 12
    assert sum(f.percussion_onset for f in frames) <= 2
