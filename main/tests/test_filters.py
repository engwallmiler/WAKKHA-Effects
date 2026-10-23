import numpy as np
import pytest
from beatlight.dsp.config import DspConfig
from beatlight.dsp.filters import FilterBank, FilterSpec, StreamingFilter
from beatlight.dsp.preprocess import AudioPreprocessor, normalize_for_analysis, stereo_to_mono


@pytest.mark.parametrize("kind,cutoffs,passed,rejected", [
    ("lowpass", (1000,), 100, 10000),
    ("highpass", (1000,), 10000, 100),
    ("bandpass", (40, 150), 80, 1000)])
def test_filter_selectivity_with_known_tones(kind, cutoffs, passed, rejected):
    t = np.arange(48000) / 48000
    x = np.column_stack((np.sin(2 * np.pi * passed * t), np.sin(2 * np.pi * rejected * t)))
    y = StreamingFilter(FilterSpec("test", kind, cutoffs), 48000, 2).process(x)
    rms = np.sqrt(np.mean(y[24000:] ** 2, axis=0))
    assert rms[0] > 0.65
    assert rms[1] < 0.01


def test_stateful_filter_matches_continuous_signal_and_reset():
    rng = np.random.default_rng(42)
    x = rng.normal(0, 0.1, (10000, 2))
    spec = FilterSpec("band", "bandpass", (40, 150))
    reference = StreamingFilter(spec, 48000, 2).process(x)
    streaming = StreamingFilter(spec, 48000, 2)
    chunked = np.concatenate([streaming.process(x[i:i + 137]) for i in range(0, len(x), 137)])
    assert chunked == pytest.approx(reference, abs=1e-12)
    streaming.reset()
    assert streaming.process(x) == pytest.approx(reference, abs=1e-12)


def test_filter_bank_keeps_bands_and_channels_independent():
    t = np.arange(24000) / 48000
    x = np.column_stack((np.sin(2 * np.pi * 80 * t), np.sin(2 * np.pi * 4000 * t)))
    bank = FilterBank((FilterSpec("bass", "lowpass", (150,)),
                       FilterSpec("treble", "highpass", (2000,))), 48000, 2)
    result = bank.process(x)
    assert np.sqrt(np.mean(result["bass"][-12000:, 0] ** 2)) > 0.65
    assert np.sqrt(np.mean(result["bass"][-12000:, 1] ** 2)) < 0.01
    assert np.sqrt(np.mean(result["treble"][-12000:, 1] ** 2)) > 0.65


def test_dc_removal_does_not_mutate_input():
    x = np.full((48000, 2), 0.4, dtype=np.float32)
    x.setflags(write=False)
    output = AudioPreprocessor(DspConfig(), 48000, 2).process(x)
    assert np.max(np.abs(output[-12000:])) < 1e-8
    assert np.all(x == np.float32(0.4))
    assert not x.flags.writeable


def test_mono_and_controlled_normalization_are_explicit():
    x = np.array([[0.001, 0.003], [-0.001, -0.003]])
    assert stereo_to_mono(x) == pytest.approx([0.002, -0.002])
    normalized, gain = normalize_for_analysis(x)
    assert gain == 4
    assert normalized == pytest.approx(x * 4)
    loud, gain = normalize_for_analysis(np.array([[2.0], [-2.0]]), target_rms=1)
    assert np.max(np.abs(loud)) <= 1
    assert gain == 0.5
    silence, gain = normalize_for_analysis(np.zeros((8, 2)))
    assert gain == 1
    assert not np.any(silence)


@pytest.mark.parametrize("spec", [FilterSpec("x", "wrong", (100,)),
    FilterSpec("x", "lowpass", (24000,)), FilterSpec("x", "bandpass", (150, 40)),
    FilterSpec("x", "highpass", (float("nan"),)), FilterSpec("x", "lowpass", (100,), 0)])
def test_invalid_filter_parameters_rejected(spec):
    with pytest.raises(ValueError):
        StreamingFilter(spec, 48000, 2)
