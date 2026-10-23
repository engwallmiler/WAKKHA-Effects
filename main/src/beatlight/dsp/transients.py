"""Transientes genéricos: fluxo espectral, ataque energético e limiar adaptativo.

Não identifica instrumentos, kicks, BPM ou estrutura musical.
"""
from collections import deque
from time import monotonic
import numpy as np
from beatlight.contracts import TransientEvent
from beatlight.dsp.spectrum import SpectrumFrame


class TransientDetector:
    def __init__(self, refractory_seconds: float = 0.09):
        self.refractory_seconds = refractory_seconds
        self.count = 0
        self.last_event: TransientEvent | None = None
        self.reset()

    def reset(self):
        self._previous = None
        self._previous_rms = 0.0
        self._history: deque[float] = deque(maxlen=96)
        self.flux, self.score, self.threshold = 0.0, 0.0, 0.08
        self._last_trigger = float("-inf")

    def process(self, frame: SpectrumFrame) -> TransientEvent | None:
        magnitude = np.sqrt(frame.power)
        rms = float(np.sqrt(frame.power.sum()))
        if self._previous is None:
            self._previous, self._previous_rms = magnitude, rms
            return None
        self.flux = float(np.maximum(magnitude - self._previous, 0).sum()
                          / max(float(magnitude.sum()), 1e-12))
        attack = max(0.0, rms - self._previous_rms) / max(rms, 1e-12)
        self.score = float(np.clip(0.65 * self.flux + 0.35 * attack, 0, 1))
        if self._history:
            center = float(np.median(self._history))
            mad = float(np.median(np.abs(np.asarray(self._history) - center)))
            self.threshold = min(0.95, max(0.08, center + 3 * mad))
        occurred_at = (frame.started_at + frame.ended_at) / 2
        event = None
        if (len(self._history) >= 8 and rms > 0.001 and self.score > self.threshold
                and occurred_at - self._last_trigger >= self.refractory_seconds):
            confidence = float(np.clip((self.score - self.threshold) / max(0.2, 1 - self.threshold), 0, 1))
            event = TransientEvent(occurred_at, monotonic(), self.score, confidence)
            self.last_event = event
            self.count += 1
            self._last_trigger = occurred_at
        self._history.append(self.score)
        self._previous, self._previous_rms = magnitude, rms
        return event
