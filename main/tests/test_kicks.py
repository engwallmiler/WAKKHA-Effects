"""Sinais com onsets conhecidos: valida comportamento, não acurácia em repertório real."""
from dataclasses import replace
import numpy as np
import pytest
from beatlight.contracts import AudioBlock
from beatlight.dsp.config import DspConfig
from beatlight.dsp.kick_config import KickConfig
from beatlight.dsp.kicks import KickDetector
from beatlight.dsp.pipeline import AudioAnalyzer


def fixture_music(rate=48000, bpm=128, gain=1.0, noisy=False, duration=7):
    t = np.arange(round(rate * duration)) / rate
    signal = 0.025 * np.sin(2 * np.pi * 55 * t) + 0.02 * np.sin(2 * np.pi * 440 * t)
    truth = np.arange(0.8, duration - 0.3, 60 / bpm)
    for onset in truth:
        age = t - onset
        a = np.maximum(age, 0)
        env = np.where(age >= 0, (1 - np.exp(-a / 0.0015)) * np.exp(-a / 0.065), 0)
        phase = 2 * np.pi * (52 * a + 65 * 0.025 * (1 - np.exp(-a / 0.025)))
        signal += 0.7 * env * np.sin(phase)
        # Chimbal no contratempo: não deve criar um segundo kick.
        ha = np.maximum(age - 30 / bpm, 0)
        signal += np.where(age >= 30 / bpm, 0.12 * np.exp(-ha / 0.025) * np.sin(2 * np.pi * 8000 * ha), 0)
    if noisy:
        signal += np.random.default_rng(72).normal(0, 0.025, len(t))
    return np.asarray(signal * gain, dtype=np.float32), truth


def blocks(signal, rate=48000, chunk=512):
    for seq, first in enumerate(range(0, len(signal), chunk)):
        x = signal[first:first + chunk]
        if x.ndim == 1:
            x = x[:, None]
        x = np.asarray(x, dtype=np.float32)
        x.setflags(write=False)
        yield AudioBlock("fixture", x, rate, x.shape[1], seq, len(x), first / rate, (first + len(x)) / rate)


def detect(signal, rate=48000, chunk=512, config=None):
    detector = KickDetector(config)
    events = {}
    for block in blocks(signal, rate, chunk):
        result = detector.push(block)
        if result:
            for event in result.events:
                events[event.occurred_at] = event
    return detector, list(events.values())


@pytest.mark.parametrize("rate,bpm,gain,noisy", [
    (44100, 90, 1.0, False), (48000, 128, 1.0, False),
    (48000, 160, 0.12, False), (44100, 138, 0.3, True),
    (48000, 120, 0.015, False)])
def test_known_kicks_have_one_detection_per_onset(rate, bpm, gain, noisy):
    signal, truth = fixture_music(rate, bpm, gain, noisy)
    detector, events = detect(signal, rate)
    times = np.array([e.occurred_at for e in events])
    assert len(times) == len(truth), (times, truth)
    assert np.max(np.abs(times - truth)) < 0.065
    assert detector.count == len(truth)
    assert all(0 < e.intensity <= 1 and 0 <= e.confidence <= 1 for e in events)
    assert all(e.detected_at >= e.occurred_at for e in events)
    assert np.min(np.diff(times)) >= 0.18


@pytest.mark.parametrize("kind", ["silence", "bass", "slow_bass", "high_percussion", "noise", "dc"])
def test_negative_signals_do_not_create_repeated_kicks(kind):
    rate = 48000
    t = np.arange(rate * 4) / rate
    if kind == "silence":
        x = np.zeros_like(t)
    elif kind == "bass":
        x = 0.6 * np.sin(2 * np.pi * 65 * t)
    elif kind == "slow_bass":
        x = (0.4 + 0.2 * np.sin(2 * np.pi * 0.6 * t)) * np.sin(2 * np.pi * 65 * t)
    elif kind == "high_percussion":
        x = 0.5 * np.exp(-(t % 0.25) / 0.025) * np.sin(2 * np.pi * 5000 * t)
    elif kind == "dc":
        x = np.full_like(t, 0.4)
    else:
        x = np.random.default_rng(1).normal(0, 0.1, len(t))
    detector, events = detect(x)
    assert not events, [e.occurred_at for e in events]
    assert detector.latest is not None


def test_chunk_sizes_and_antiphase_channels_preserve_decisions():
    x, _ = fixture_music(duration=4)
    _, reference = detect(x, chunk=512)
    stereo = np.column_stack((x, -x))
    for chunk in (113, 1024, 2048):
        detector, events = detect(stereo, chunk=chunk)
        assert [e.occurred_at for e in events] == pytest.approx([e.occurred_at for e in reference])
        assert len(detector._pending) < 2048
        assert len(detector.latest.history) <= 200
        assert len(detector.latest.events) <= 16


def test_kicks_are_independent_of_display_fft_and_filters():
    x, truth = fixture_music(duration=4)
    configs = (DspConfig(), DspConfig(fft_size=8192, fft_overlap=25, filter_mode="highpass", filter_low_hz=4000, filter_high_hz=12000))
    counts = []
    for config in configs:
        analyzer = AudioAnalyzer(config=config)
        result = None
        for block in blocks(x):
            result = analyzer.process(block)
        assert not result.kick_error
        counts.append(result.kicks.count)
    assert counts == [len(truth), len(truth)]


def test_gap_discards_kick_windows_and_old_history(block_factory):
    analyzer = AudioAnalyzer()
    x, _ = fixture_music(duration=2)
    for block in blocks(x):
        previous = analyzer.process(block)
    gap = block_factory(np.zeros((512, 1)), sequence=1000)
    after = analyzer.process(replace(gap, discontinuity=True))
    assert after.kicks is None
    assert analyzer._kicks.count == previous.kicks.count
    assert not analyzer._kicks._intervals


def test_optional_kick_failure_keeps_spectrum_and_meters(block_factory, caplog, monkeypatch):
    analyzer = AudioAnalyzer()
    def fail(block):
        raise RuntimeError("kick-test-failure")
    monkeypatch.setattr(analyzer._kicks, "push", fail)
    for seq in range(8):
        result = analyzer.process(block_factory(np.zeros((512, 2)), sequence=seq))
        assert result.kicks is None
        assert result.kick_error == "kick-test-failure"
        assert not result.analysis_error
        assert result.rms_db == (-120, -120)
    assert result.spectral is not None
    assert sum(r.message == "kick_analysis_failed" for r in caplog.records) == 1


@pytest.mark.parametrize("kwargs", [{"kick_low_hz": 200}, {"kick_high_hz": 900},
    {"kick_sensitivity": 0}, {"kick_refractory_ms": 10}, {"kick_floor_db": -10},
    {"kick_sensitivity": True}, {"kick_low_hz": float("nan")}])
def test_invalid_kick_config_rejected(kwargs):
    with pytest.raises(ValueError):
        KickConfig(**kwargs)


def test_intensity_tracks_kick_peak_instead_of_early_onset():
    x, truth = fixture_music(duration=4)
    _, events = detect(x)
    assert len(events) == len(truth)
    assert all(e.intensity > 0.85 for e in events)


def test_quieter_kick_has_lower_relative_strength():
    x, truth = fixture_music(duration=4)
    # Reduz um kick após o detector ter histórico de eventos fortes.
    first = int(truth[4] * 48000)
    x[first:first + int(0.3 * 48000)] *= 0.4
    _, events = detect(x)
    assert len(events) == len(truth)
    assert events[4].intensity < events[3].intensity * 0.7


def test_refractory_rejects_repeated_low_frequency_hits():
    x, truth = fixture_music(bpm=160, duration=4)
    # 400 ms impede confirmação de todos os ataques a cada 375 ms.
    _, events = detect(x, config=KickConfig(kick_refractory_ms=400))
    assert 0 < len(events) < len(truth)
    assert all(b.occurred_at - a.occurred_at >= 0.4 for a, b in zip(events, events[1:]))


def test_spectral_failure_does_not_disable_kicks(block_factory):
    analyzer = AudioAnalyzer(config=DspConfig(filter_mode="bandpass", filter_low_hz=10000, filter_high_hz=15000))
    result = analyzer.process(block_factory(np.zeros((8192, 2)), rate=16000))
    assert result.analysis_error
    assert not result.kick_error
    assert result.kicks is not None


def test_kick_failure_can_recover_on_new_format(block_factory, monkeypatch):
    analyzer = AudioAnalyzer()
    original = analyzer._kicks.push
    def fail(block):
        raise RuntimeError("test failure")
    monkeypatch.setattr(analyzer._kicks, "push", fail)
    assert analyzer.process(block_factory(np.zeros((2048, 2)))).kick_error
    monkeypatch.setattr(analyzer._kicks, "push", original)
    result = analyzer.process(block_factory(np.zeros((2048, 2)), rate=44100, sequence=1))
    assert result.kicks is not None
    assert not result.kick_error


def test_detector_handles_driver_flags_without_pipeline():
    detector = KickDetector()
    for block in blocks(np.zeros(48000)):
        detector.push(block)
    assert detector.latest.ready
    discontinuous = replace(block, sequence=block.sequence + 1, status_flags=1)
    assert detector.push(discontinuous) is None
    assert not detector._history
    assert detector._previous_mag is None
