"""Parâmetros do DSP, independentes da persistência e da interface."""
from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class DspConfig:
    fft_size: int = 2048
    fft_overlap: int = 75
    remove_dc: bool = True
    filter_mode: str = "none"
    filter_low_hz: float = 40.0
    filter_high_hz: float = 150.0
    low_mid_hz: float = 250.0
    mid_high_hz: float = 2000.0

    def __post_init__(self):
        if type(self.fft_size) is not int or self.fft_size not in (1024, 2048, 4096, 8192):
            raise ValueError("FFT deve ter 1024, 2048, 4096 ou 8192 amostras.")
        if type(self.fft_overlap) is not int or self.fft_overlap not in (25, 50, 75):
            raise ValueError("Sobreposição FFT deve ser 25, 50 ou 75%.")
        if type(self.remove_dc) is not bool:
            raise ValueError("Remoção de DC deve ser booleana.")
        if self.filter_mode not in ("none", "lowpass", "highpass", "bandpass"):
            raise ValueError("Tipo de pré-filtro inválido.")
        for value in (self.filter_low_hz, self.filter_high_hz, self.low_mid_hz, self.mid_high_hz):
            if type(value) not in (float, int) or not math.isfinite(value) or not 1 <= value <= 20000:
                raise ValueError("Frequências de análise devem estar entre 1 e 20.000 Hz.")
        if self.filter_low_hz >= self.filter_high_hz:
            raise ValueError("O corte inferior deve ser menor que o superior.")
        if not 20 < self.low_mid_hz < self.mid_high_hz < 20000:
            raise ValueError("Bandas devem respeitar 20 Hz < graves/médios < médios/agudos < 20 kHz.")

    @property
    def hop_size(self) -> int:
        return self.fft_size * (100 - self.fft_overlap) // 100

    @property
    def bands(self) -> tuple[tuple[float, float], ...]:
        return ((20.0, self.low_mid_hz), (self.low_mid_hz, self.mid_high_hz),
                (self.mid_high_hz, 20000.0))
