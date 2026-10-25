"""FFT incremental com Hann, sobreposição e potência estéreo sem cancelamento."""
from dataclasses import dataclass
import numpy as np
from beatlight.dsp.config import DspConfig


@dataclass(frozen=True, slots=True)
class SpectrumFrame:
    id: int
    power: np.ndarray
    frequencies: np.ndarray
    display_frequencies: tuple[float, ...]
    display_db: tuple[float, ...]
    band_levels_db: tuple[float, ...]
    band_fraction: tuple[float, ...]
    dominant_hz: float
    rms_db: float
    started_at: float
    ended_at: float


def power_db(power):
    return 10 * np.log10(np.maximum(power, 1e-12))


class StreamingSpectrum:
    def __init__(self, config: DspConfig, columns: int = 96):
        if type(columns) is not int or not 8 <= columns <= 512:
            raise ValueError("Quantidade de colunas espectrais inválida.")
        self.config, self.columns = config, columns
        self._signature = None
        self._frame_id = 0
        self._pending = np.empty((0, 0))
        self._pending_at = 0.0
        self._window = np.hanning(config.fft_size)
        self._normalization = config.fft_size * float(np.sum(self._window ** 2))

    def reset(self):
        self._signature = None
        self._pending = np.empty((0, 0))

    def _configure(self, sample_rate: int, channels: int):
        if sample_rate <= 40 or channels < 1:
            raise ValueError("Formato de áudio incompatível com análise espectral.")
        self._signature = sample_rate, channels
        self._pending = np.empty((0, channels), dtype=np.float64)
        self._frequencies = np.fft.rfftfreq(self.config.fft_size, 1 / sample_rate)
        self._weights = np.full(len(self._frequencies), 2.0)
        self._weights[0] = self._weights[-1] = 1.0  # DC e Nyquist não têm par negativo
        upper = min(20000.0, sample_rate / 2)
        edges = np.geomspace(20.0, upper, self.columns + 1)
        self._display_centers = tuple(float(f) for f in np.sqrt(edges[:-1] * edges[1:]))
        self._visible = (self._frequencies >= 20) & (self._frequencies <= upper)
        self._groups = np.clip(np.searchsorted(edges, self._frequencies[self._visible], side="right") - 1,
                               0, self.columns - 1)
        self._band_masks = tuple((self._frequencies >= low) & (
            self._frequencies <= high if i == 2 else self._frequencies < high)
            for i, (low, high) in enumerate(self.config.bands))

    def push(self, samples: np.ndarray, sample_rate: int, acquired_at: float) -> list[SpectrumFrame]:
        x = np.asarray(samples, dtype=np.float64)
        if x.ndim != 2 or x.shape[1] < 1 or not np.isfinite(x).all():
            raise ValueError("Amostras inválidas para FFT.")
        if (sample_rate, x.shape[1]) != self._signature:
            self._configure(sample_rate, x.shape[1])
        if not len(x):
            return []
        if not len(self._pending):
            self._pending_at = acquired_at
        self._pending = np.concatenate((self._pending, x), axis=0)
        result = []
        n, hop = self.config.fft_size, self.config.hop_size
        while len(self._pending) >= n:
            transformed = np.fft.rfft(self._pending[:n] * self._window[:, None], axis=0)
            # Média das potências dos canais preserva sinais estéreo em oposição de fase.
            power = np.mean(np.abs(transformed) ** 2, axis=1) * self._weights / self._normalization
            bars = np.bincount(self._groups, weights=power[self._visible], minlength=self.columns)
            band_power = np.array([power[mask].sum() for mask in self._band_masks])
            total_bands = float(band_power.sum())
            fractions = band_power / total_bands if total_bands > 1e-12 else np.zeros(3)
            peak = int(np.argmax(np.where(self._visible, power, 0)))
            dominant = float(self._frequencies[peak]) if power[peak] > 1e-12 else 0.0
            self._frame_id += 1
            power.setflags(write=False)
            result.append(SpectrumFrame(
                self._frame_id, power, self._frequencies, self._display_centers,
                tuple(float(v) for v in power_db(bars)),
                tuple(float(v) for v in power_db(band_power)),
                tuple(float(v) for v in fractions), dominant, float(power_db(power.sum())),
                self._pending_at, self._pending_at + n / sample_rate,
            ))
            self._pending = self._pending[hop:]
            self._pending_at += hop / sample_rate
        # Copiar só o restante evita reter buffers grandes em visões pequenas.
        self._pending = self._pending.copy()
        return result
