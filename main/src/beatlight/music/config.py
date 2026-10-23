from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class BeatConfig:
    beat_min_bpm: float = 90.0
    beat_max_bpm: float = 160.0
    beat_hold_seconds: float = 4.0

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("Parâmetros de BPM devem ser números finitos.")
        if not 40 <= self.beat_min_bpm < self.beat_max_bpm <= 240:
            raise ValueError("Faixa de BPM inválida: use 40–240, com mínimo menor que máximo.")
        if self.beat_max_bpm - self.beat_min_bpm < 10:
            raise ValueError("A faixa de BPM deve ter pelo menos 10 BPM de largura.")
        if not 1 <= self.beat_hold_seconds <= 12:
            raise ValueError("Tempo de manutenção do sincronismo deve estar entre 1 e 12 segundos.")
