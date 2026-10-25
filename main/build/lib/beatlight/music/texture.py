"""Envelope grave e densidade espectral, independentes de kicks e BPM."""
from collections import deque
import math
from beatlight.contracts import TextureSnapshot


def clamp(value):
    return min(1.0, max(0.0, value))


class TextureTracker:
    def __init__(self):
        self.at = None
        self.bass = self.activity = self.density = self.reference = 0.0
        self.onsets = deque(maxlen=128)

    def process(self, feature):
        at = feature.at
        if self.at is not None and at < self.at:
            raise ValueError("Tempo da textura deve avançar monotonamente.")
        if self.at is not None and at - self.at > 0.75:
            self.__init__()
        dt = min(0.2, max(0.001, at - self.at)) if self.at is not None else 0.01
        self.at = at
        if not all(math.isfinite(v) for v in (feature.bass_db, feature.rms_db, feature.brightness, *feature.texture_bands_db)):
            raise ValueError("Descritores de textura inválidos.")
        if feature.onset:
            self.onsets.append(at)
        while self.onsets and self.onsets[0] < at - 2:
            self.onsets.popleft()
        rate = len(self.onsets) / 2
        bands = feature.texture_bands_db
        occupancy = (sum(v > max(-65.0, max(bands) - 28) for v in bands) / len(bands)) if bands else 0.0
        audible = feature.rms_db > -65
        target_density = clamp(occupancy * 0.8 + min(1, rate / 10) * 0.2) if audible else 0.0
        target_bass = clamp((feature.bass_db + 65) / 50) if audible else 0.0
        power = 10 ** (feature.bass_db / 10)
        attack = clamp((power - self.reference) / max(power + self.reference, 1e-12)) if audible else 0.0
        self.reference += (power - self.reference) * (1 - math.exp(-dt / 0.18))
        self.bass += (target_bass - self.bass) * (1 - math.exp(-dt / (0.06 if target_bass > self.bass else 0.25)))
        self.activity += (attack - self.activity) * (1 - math.exp(-dt / 0.08))
        self.density += (target_density - self.density) * (1 - math.exp(-dt / 0.3))
        if not audible:
            self.onsets.clear()
            rate = 0.0
        return TextureSnapshot(at, feature.bass_db, clamp(self.bass), clamp(self.activity),
            clamp(self.density), occupancy if audible else 0.0, rate, clamp(feature.brightness), not audible)
