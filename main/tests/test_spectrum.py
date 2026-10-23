import numpy as np
import pytest
from beatlight.dsp.config import DspConfig
from beatlight.dsp.spectrum import StreamingSpectrum


@pytest.mark.parametrize("rate", [44100, 48000])
def test_calibrated_sine_and_antiphase_stereo(rate):
    n = 4096
    frequency = 85 * rate / n
    t = np.arange(n) / rate
    tone = 0.5 * np.sin(2 * np.pi * frequency * t)
    spectrum = StreamingSpectrum(DspConfig(fft_size=n, remove_dc=False))
    frame = spectrum.push(np.column_stack((tone, -tone)), rate, 100)[0]
    assert frame.dominant_hz == pytest.approx(frequency)
    assert frame.rms_db == pytest.approx(-9.0309, abs=0.001)
    assert frame.band_levels_db[1] == pytest.approx(-9.0309, abs=0.001)
    assert frame.band_fraction[1] > 0.999
    assert sum(frame.band_fraction) == pytest.approx(1)
    assert len(frame.display_db) == 96
    assert np.isfinite(frame.display_db).all()
    assert frame.ended_at - frame.started_at == pytest.approx(n / rate)


@pytest.mark.parametrize("frequency,band", [(93.75, 0), (1500, 1), (6000, 2)])
def test_frequency_is_assigned_to_expected_band(frequency, band):
    rate, n = 48000, 4096
    t = np.arange(n) / rate
    frame = StreamingSpectrum(DspConfig(fft_size=n)).push(
        (0.3 * np.sin(2 * np.pi * frequency * t))[:, None], rate, 0)[0]
    assert frame.band_fraction[band] > 0.995
    assert abs(frame.dominant_hz - frequency) <= rate / n


def test_chunking_preserves_fft_frames_and_timestamps():
    config = DspConfig(fft_size=2048, fft_overlap=75)
    t = np.arange(12345) / 48000
    signal = np.column_stack((0.4 * np.sin(2 * np.pi * 1000 * t), 0.2 * np.sin(2 * np.pi * 4000 * t)))
    whole = StreamingSpectrum(config).push(signal, 48000, 10)
    streaming = StreamingSpectrum(config)
    chunked = []
    for first in range(0, len(signal), 113):
        chunked.extend(streaming.push(signal[first:first + 113], 48000, 10 + first / 48000))
    assert len(chunked) == len(whole) == 21
    for a, b in zip(chunked, whole):
        assert a.display_db == pytest.approx(b.display_db, abs=1e-9)
        assert a.started_at == pytest.approx(b.started_at)
    assert len(streaming._pending) < config.fft_size


@pytest.mark.parametrize("nyquist", [False, True])
def test_dc_and_nyquist_have_correct_one_sided_energy(nyquist):
    signal = np.full((2048, 1), 0.25)
    if nyquist:
        signal[1::2] *= -1
    frame = StreamingSpectrum(DspConfig(remove_dc=False)).push(signal, 48000, 0)[0]
    assert frame.rms_db == pytest.approx(20 * np.log10(0.25), abs=1e-9)


def test_silence_is_finite_and_has_no_dominant_frequency():
    frame = StreamingSpectrum(DspConfig()).push(np.zeros((2048, 2)), 48000, 0)[0]
    assert frame.rms_db == -120
    assert frame.dominant_hz == 0
    assert frame.band_fraction == (0, 0, 0)
    assert frame.display_db == (-120,) * 96


def test_reset_discards_audio_before_a_gap():
    spectrum = StreamingSpectrum(DspConfig(fft_size=1024))
    assert not spectrum.push(np.ones((512, 1)), 48000, 0)
    spectrum.reset()
    assert not spectrum.push(np.zeros((512, 1)), 48000, 2)
    frame = spectrum.push(np.zeros((512, 1)), 48000, 2 + 512 / 48000)[0]
    assert frame.rms_db == -120
    assert frame.started_at == 2


@pytest.mark.parametrize("size,overlap", [(1024, 25), (2048, 50), (4096, 75), (8192, 75)])
def test_fft_settings_control_resolution_and_frame_spacing(size, overlap):
    config = DspConfig(fft_size=size, fft_overlap=overlap)
    frames = StreamingSpectrum(config).push(np.zeros((size + config.hop_size * 2, 2)), 44100, 5)
    assert len(frames) == 3
    assert frames[1].started_at - frames[0].started_at == pytest.approx(config.hop_size / 44100)
