"""Parâmetros do detector de kicks, independentes da visualização espectral."""
from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class KickConfig:
    kick_low_hz: float = 40.0
    kick_high_hz: float = 150.0
    kick_sensitivity: float = 1.0
    kick_refractory_ms: float = 180.0
    kick_floor_db: float = -60.0

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("Parâmetros de kick devem ser números finitos.")
        if not 20 <= self.kick_low_hz < self.kick_high_hz <= 400:
            raise ValueError("Faixa de kick inválida: use 20–400 Hz, com corte inferior menor que o superior.")
        if self.kick_high_hz - self.kick_low_hz < 25:
            raise ValueError("A faixa de kick deve ter pelo menos 25 Hz de largura.")
        if not 0.5 <= self.kick_sensitivity <= 2.0:
            raise ValueError("Sensibilidade de kick deve estar entre 0,5 e 2,0.")
        if not 100 <= self.kick_refractory_ms <= 400:
            raise ValueError("Intervalo mínimo de kick deve estar entre 100 e 400 ms.")
        if not -90 <= self.kick_floor_db <= -30:
            raise ValueError("Piso de kick deve estar entre −90 e −30 dBFS.")
