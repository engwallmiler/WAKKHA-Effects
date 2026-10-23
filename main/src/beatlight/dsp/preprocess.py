"""Operações explícitas de análise; nunca modificam o bloco capturado."""
import numpy as np
from beatlight.dsp.config import DspConfig
from beatlight.dsp.filters import FilterSpec, StreamingFilter


def stereo_to_mono(samples: np.ndarray) -> np.ndarray:
    x = np.asarray(samples, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] < 1:
        raise ValueError("Esperado um bloco [frames, canais].")
    return x.mean(axis=1)


def normalize_for_analysis(samples: np.ndarray, target_rms: float = 0.1,
                           max_gain: float = 4.0) -> tuple[np.ndarray, float]:
    """Normalização opcional e limitada. Não é ativada no pipeline padrão."""
    x = np.asarray(samples, dtype=np.float64)
    if not 0 < target_rms <= 1 or not 1 <= max_gain <= 100 or not np.isfinite(x).all():
        raise ValueError("Parâmetros ou amostras inválidos para normalização.")
    if not x.size:
        return x.copy(), 1.0
    rms, peak = float(np.sqrt(np.mean(x * x))), float(np.max(np.abs(x)))
    if peak <= 1e-12:
        return x.copy(), 1.0
    gain = min(target_rms / max(rms, 1e-12), max_gain, 1.0 / peak)
    return x * gain, gain


class AudioPreprocessor:
    def __init__(self, config: DspConfig, sample_rate: int, channels: int):
        self.filters = []
        if config.remove_dc:
            self.filters.append(StreamingFilter(FilterSpec("dc", "highpass", (20.0,), 2),
                                                sample_rate, channels))
        if config.filter_mode != "none":
            cutoffs = ((config.filter_low_hz, config.filter_high_hz)
                       if config.filter_mode == "bandpass" else
                       (config.filter_low_hz,) if config.filter_mode == "highpass" else
                       (config.filter_high_hz,))
            self.filters.append(StreamingFilter(FilterSpec("analysis", config.filter_mode, cutoffs),
                                                sample_rate, channels))

    def process(self, samples: np.ndarray) -> np.ndarray:
        x = np.asarray(samples, dtype=np.float64)
        for filt in self.filters:
            x = filt.process(x)
        return x
