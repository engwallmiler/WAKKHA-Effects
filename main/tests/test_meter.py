import numpy as np
import pytest
from beatlight.dsp.meter import LevelAnalyzer


def test_known_stereo_sine_rms_and_peak(block_factory):
    t = np.arange(4800) / 48000
    sine = np.sin(2 * np.pi * 1000 * t)
    snap = LevelAnalyzer().process(block_factory(np.column_stack((sine * 0.5, sine * 0.25))))
    assert snap.rms_db == pytest.approx((-9.0309, -15.0515), abs=0.01)
    assert snap.peak_db == pytest.approx((-6.0206, -12.0412), abs=0.01)
    assert not snap.silent
    assert not snap.clipping
    assert len(snap.waveform) == 2
    assert len(snap.waveform[0]) <= 960


def test_silence_is_finite_and_clipping_is_reported(block_factory):
    analyzer = LevelAnalyzer()
    silent = analyzer.process(block_factory(np.zeros((512, 2))))
    assert silent.silent
    assert silent.rms_db == (-120, -120)
    clipped = analyzer.process(block_factory(np.ones((512, 2)), sequence=1))
    assert clipped.clipping
    assert not clipped.silent


def test_envelope_preserves_single_sample_transient(block_factory):
    signal = np.zeros((1024, 2))
    signal[501, 0] = 0.9
    snapshot = LevelAnalyzer().process(block_factory(signal))
    assert max(snapshot.waveform[0]) == pytest.approx(0.9)


def test_sequence_gap_and_driver_flags_count_once(block_factory):
    analyzer = LevelAnalyzer()
    analyzer.process(block_factory(np.zeros((512, 2)), sequence=0))
    gap = analyzer.process(block_factory(np.zeros((512, 2)), sequence=4, discontinuity=True))
    assert gap.continuity_errors == 1


def test_nan_rejected(block_factory):
    with pytest.raises(ValueError, match="inválido"):
        LevelAnalyzer().process(block_factory([[float("nan"), 0]]))
