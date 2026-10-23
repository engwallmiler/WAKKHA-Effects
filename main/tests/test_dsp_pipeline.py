from time import monotonic
import numpy as np
import pytest
from beatlight.contracts import AudioBlock
from beatlight.dsp.config import DspConfig
from beatlight.dsp.pipeline import AudioAnalyzer


def analyze(signal, config=None, rate=48000, gain=1.0):
    analyzer = AudioAnalyzer(config=config or DspConfig())
    start = monotonic() - len(signal) / rate
    snapshots = []
    for seq, first in enumerate(range(0, len(signal), 512)):
        x = np.asarray(signal[first:first + 512] * gain, dtype=np.float32)
        if x.ndim == 1:
            x = x[:, None]
        x.setflags(write=False)
        block = AudioBlock("test", x, rate, x.shape[1], seq, len(x),
                           start + first / rate, start + (first + len(x)) / rate)
        snapshots.append(analyzer.process(block))
    return snapshots


def test_analysis_filter_preserves_original_meter_and_waveform():
    t = np.arange(48000) / 48000
    x = np.column_stack((0.5 * np.sin(2 * np.pi * 1000 * t), 0.5 * np.sin(2 * np.pi * 1000 * t)))
    raw = analyze(x, DspConfig(remove_dc=False))[-1]
    filtered = analyze(x, DspConfig(filter_mode="bandpass", filter_low_hz=40, filter_high_hz=150))[-1]
    assert filtered.rms_db == pytest.approx(raw.rms_db)
    assert filtered.peak_db == pytest.approx(raw.peak_db)
    assert filtered.waveform == raw.waveform
    assert filtered.spectral.total_rms_db < raw.spectral.total_rms_db - 50
    assert filtered.spectral.filter_mode == "bandpass"


def test_dc_is_removed_from_analysis_but_measured_at_input():
    snapshot = analyze(np.full((48000, 2), 0.4))[-1]
    assert snapshot.rms_db == pytest.approx((20 * np.log10(0.4),) * 2, abs=1e-6)
    assert snapshot.spectral.total_rms_db < -110
    assert snapshot.spectral.dc_removed


def test_gap_does_not_merge_old_and_new_fft_windows(block_factory):
    analyzer = AudioAnalyzer(config=DspConfig(fft_size=1024, remove_dc=False))
    assert analyzer.process(block_factory(np.ones((512, 2)), sequence=0)).spectral is None
    after_gap = analyzer.process(block_factory(np.zeros((512, 2)), sequence=5))
    assert after_gap.spectral is None
    complete = analyzer.process(block_factory(np.zeros((512, 2)), sequence=6))
    assert complete.spectral.total_rms_db == -120
    assert complete.continuity_errors == 1
    assert complete.spectral.transient_count == 0


def test_optional_dsp_failure_keeps_meters_and_avoids_log_storm(block_factory, caplog):
    analyzer = AudioAnalyzer(config=DspConfig(filter_mode="bandpass", filter_low_hz=10000, filter_high_hz=15000))
    for seq in range(5):
        result = analyzer.process(block_factory(np.full((512, 2), 0.2), rate=16000, sequence=seq))
        assert result.spectral is None
        assert "Nyquist" in result.analysis_error
        assert result.rms_db == pytest.approx((-13.9794,) * 2, abs=0.001)
    assert sum(r.message == "spectral_analysis_failed" for r in caplog.records) == 1
    # Outro formato válido permite recuperar sem preservar um erro de outra fonte.
    recovered = analyzer.process(block_factory(np.zeros((2048, 2)), rate=48000, sequence=5))
    assert recovered.spectral is not None
    assert not recovered.analysis_error


def test_steady_bass_is_not_repeatedly_classified_as_transients():
    t = np.arange(48000 * 3) / 48000
    result = analyze(0.5 * np.sin(2 * np.pi * 70 * t))[-1]
    assert result.spectral.transient_count == 0


def test_bursts_detected_with_valid_confidence_and_refractory_spacing():
    rate = 48000
    t = np.arange(rate * 3) / rate
    envelope = np.where(t < 0.5, 0.01, 0.01 + 0.5 * np.exp(-(((t - 0.5) % 0.5) * 25)))
    signal = envelope * np.sin(2 * np.pi * 80 * t)
    snapshots = analyze(signal, DspConfig(remove_dc=False))
    events = {}
    for snapshot in snapshots:
        event = snapshot.spectral.last_transient if snapshot.spectral else None
        if event:
            events[event.occurred_at] = event
    assert 4 <= len(events) <= 6
    timestamps = sorted(events)
    assert all(b - a >= 0.09 for a, b in zip(timestamps, timestamps[1:]))
    for event in events.values():
        assert 0 <= event.confidence <= 1
        assert 0 < event.intensity <= 1
        assert event.detected_at >= event.occurred_at
    assert snapshots[-1].spectral.transient_count == len(events)
    quieter = analyze(signal, DspConfig(remove_dc=False), gain=0.15)[-1]
    assert quieter.spectral.transient_count == len(events)


@pytest.mark.parametrize("kwargs", [{"fft_size": 513}, {"fft_size": True}, {"fft_overlap": 100},
    {"remove_dc": 1}, {"filter_mode": "other"}, {"filter_low_hz": float("nan")},
    {"filter_low_hz": 500}, {"low_mid_hz": 3000}, {"mid_high_hz": 20000}])
def test_invalid_dsp_settings_are_rejected(kwargs):
    with pytest.raises(ValueError):
        DspConfig(**kwargs)
