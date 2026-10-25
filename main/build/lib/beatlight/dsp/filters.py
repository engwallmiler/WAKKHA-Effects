"""Filtros causais SOS com estado preservado entre blocos, sem Qt ou captura."""
from dataclasses import dataclass
import numpy as np
from scipy.signal import butter, sosfilt


@dataclass(frozen=True, slots=True)
class FilterSpec:
    name: str
    kind: str
    cutoffs_hz: tuple[float, ...]
    order: int = 4


class StreamingFilter:
    def __init__(self, spec: FilterSpec, sample_rate: int, channels: int):
        if spec.kind not in ("lowpass", "highpass", "bandpass"):
            raise ValueError("Tipo de filtro inválido.")
        count = 2 if spec.kind == "bandpass" else 1
        if (len(spec.cutoffs_hz) != count or channels < 1 or sample_rate <= 0
                or type(spec.order) is not int or not 1 <= spec.order <= 8):
            raise ValueError("Parâmetros do filtro inválidos.")
        cutoffs = np.asarray(spec.cutoffs_hz, dtype=np.float64)
        if not np.isfinite(cutoffs).all() or np.any(cutoffs <= 0) or np.any(cutoffs >= sample_rate / 2):
            raise ValueError("Cortes do filtro devem ficar abaixo da frequência de Nyquist.")
        if count == 2 and cutoffs[0] >= cutoffs[1]:
            raise ValueError("Cortes do passa-banda estão invertidos.")
        self.channels = channels
        self.sos = butter(spec.order, cutoffs if count == 2 else cutoffs[0],
                          btype=spec.kind, fs=sample_rate, output="sos")
        self._state = np.zeros((len(self.sos), 2, channels), dtype=np.float64)

    def process(self, samples: np.ndarray) -> np.ndarray:
        x = np.asarray(samples, dtype=np.float64)
        if x.ndim != 2 or x.shape[1] != self.channels or not np.isfinite(x).all():
            raise ValueError("Bloco inválido para o filtro.")
        if not len(x):
            return x.copy()
        result, self._state = sosfilt(self.sos, x, axis=0, zi=self._state)
        return result

    def reset(self) -> None:
        self._state.fill(0)


class FilterBank:
    """Várias bandas independentes; conversão de entrada compartilhada."""
    def __init__(self, specs: tuple[FilterSpec, ...], sample_rate: int, channels: int):
        if len({s.name for s in specs}) != len(specs):
            raise ValueError("Os nomes dos filtros devem ser únicos.")
        self.filters = {s.name: StreamingFilter(s, sample_rate, channels) for s in specs}

    def process(self, samples: np.ndarray) -> dict[str, np.ndarray]:
        x = np.asarray(samples, dtype=np.float64)
        return {name: filt.process(x) for name, filt in self.filters.items()}

    def reset(self) -> None:
        for filt in self.filters.values():
            filt.reset()
