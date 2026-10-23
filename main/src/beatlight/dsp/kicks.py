"""Detector causal heurístico: banda, ataque, fluxo, contexto e regularidade.

Recebe áudio original multicanal. Nenhum relógio musical ou filtro da GUI é
usado. A média das potências por canal evita cancelamento de fase estéreo.
"""
from collections import deque
from dataclasses import replace
from time import monotonic
import numpy as np
from beatlight.contracts import AudioBlock, KickEvent, KickSnapshot
from beatlight.dsp.filters import FilterSpec, StreamingFilter
from beatlight.dsp.kick_config import KickConfig


class KickDetector:
    def __init__(self, config: KickConfig | None = None):
        self.config = config or KickConfig()
        self.count = 0
        self.frame_id = 0
        self.reset()

    def reset(self):
        # Não mistura histórico através de perdas ou trocas de formato.
        self._signature = None
        self._pending = self._band_pending = None
        self._energies = deque(maxlen=100)
        self._scores = deque(maxlen=100)
        self._attacks = deque(maxlen=3)
        self._intervals = deque(maxlen=8)
        self._events = deque(maxlen=16)
        self._history = deque(maxlen=200)
        self._previous_mag = None
        self._last_time = None
        self._last_sequence = None
        self.latest = None

    def _setup(self, block):
        self._rate = block.sample_rate
        self._size = 2048
        self._hop = max(1, round(self._rate * 0.01))
        if self._hop >= self._size:
            raise ValueError("Taxa de amostragem não suportada pelo detector de kick.")
        cfg = self.config
        self._filter = StreamingFilter(FilterSpec("kick", "bandpass",
            (cfg.kick_low_hz, cfg.kick_high_hz), 4), self._rate, block.channels)
        self._window = np.hanning(self._size)
        self._weights = self._window ** 2 / np.sum(self._window ** 2)
        freqs = np.fft.rfftfreq(self._size, 1 / self._rate)
        self._mask = (freqs >= cfg.kick_low_hz) & (freqs <= cfg.kick_high_hz)
        if not self._mask.any():
            raise ValueError("Faixa de kick estreita demais para a resolução do detector.")
        self._pending = np.empty((0, block.channels), dtype=np.float64)
        self._band_pending = self._pending.copy()
        self._origin = block.acquired_at
        self._signature = block.source_id, block.sample_rate, block.channels

    def push(self, block: AudioBlock) -> KickSnapshot | None:
        signature = block.source_id, block.sample_rate, block.channels
        gap = (block.discontinuity or bool(block.status_flags) or
               (self._last_sequence is not None and block.sequence != self._last_sequence + 1))
        if signature != self._signature or gap:
            self.reset()
            self._setup(block)
        self._last_sequence = block.sequence
        x = np.asarray(block.samples, dtype=np.float64)
        band = self._filter.process(x)
        self._pending = np.concatenate((self._pending, x))
        self._band_pending = np.concatenate((self._band_pending, band))
        while len(self._pending) >= self._size:
            self._analyze(self._pending[:self._size], self._band_pending[:self._size])
            self._pending = self._pending[self._hop:]
            self._band_pending = self._band_pending[self._hop:]
            self._origin += self._hop / self._rate
        return self.latest

    def _analyze(self, x, band):
        cfg = self.config
        energy = float(np.sum(np.mean(band * band, axis=1) * self._weights))
        power = np.mean(np.abs(np.fft.rfft(x * self._window[:, None], axis=0)) ** 2, axis=1)
        # Escala absoluta não é usada pelo fluxo, somente diferenças relativas.
        mag = np.sqrt(power[self._mask])
        flux = (float(np.sum(np.maximum(0, mag - self._previous_mag))) /
                max(float(np.sum(mag)), 1e-12)) if self._previous_mag is not None else 0.0
        self._previous_mag = mag
        low_fraction = float(np.sum(power[self._mask]) / max(float(np.sum(power)), 1e-12))
        reference = self._attacks[0] if self._attacks else energy
        attack = float(np.clip((energy - reference) / max(energy + reference, 1e-12), 0, 1))
        baseline = float(np.median(self._energies)) if self._energies else energy
        contrast = energy / max(baseline, 1e-10)
        novelty = float(np.clip((contrast - 1) / 4, 0, 1))
        regularity = 0.0
        if len(self._intervals) >= 3:
            intervals = np.asarray(self._intervals)
            period = float(np.median(intervals))
            consistency = max(0.0, 1 - float(np.median(np.abs(intervals - period))) / period * 5)
            distance = abs((self._origin + self._size / (2 * self._rate) - self._last_time) / period - 1)
            regularity = consistency * max(0.0, 1 - distance * 4)
        score = float(np.clip(0.45 * attack + 0.35 * flux + 0.2 * novelty + 0.04 * regularity, 0, 1))
        median = float(np.median(self._scores)) if self._scores else 0.0
        mad = float(np.median(np.abs(np.asarray(self._scores) - median))) if self._scores else 0.0
        threshold = min(0.85, max(0.20, median + 3 * mad + 0.08) / cfg.kick_sensitivity)
        center = self._origin + self._size / (2 * self._rate)
        ready = len(self._scores) >= 25
        spacing = self._last_time is None or center - self._last_time >= cfg.kick_refractory_ms / 1000
        db = max(-120.0, 10 * np.log10(max(energy, 1e-12)))
        # Combina evidências: amplitude isolada não confirma um evento.
        if (ready and spacing and db >= cfg.kick_floor_db and low_fraction >= 0.08
                and attack >= 0.08 and flux >= 0.035 and contrast >= 1.3 and score >= threshold):
            if self._last_time is not None:
                interval = center - self._last_time
                if 0.2 <= interval <= 1.5:
                    self._intervals.append(interval)
                else:
                    self._intervals.clear()
            self._last_time = center
            self._event_peak = energy
            self._event_reference = max(energy, float(np.percentile(self._energies, 95)))
            strength = float(np.clip(np.sqrt(energy / max(self._event_reference, 1e-12)), 0, 1))
            confidence = float(np.clip(0.35 + 0.25 * attack + 0.2 * flux + 0.15 * novelty + 0.05 * regularity, 0, 0.98))
            event = KickEvent(center, monotonic(), strength, confidence)
            self._events.append(event)
            self.count += 1
        if self._events and center - self._last_time <= 0.09:
            # Confirma cedo; refina a força nos próximos 90 ms sem duplicar o evento.
            self._event_peak = max(self._event_peak, energy)
            strength = float(np.clip(np.sqrt(self._event_peak /
                max(self._event_peak, self._event_reference, 1e-12)), 0, 1))
            self._events[-1] = replace(self._events[-1], intensity=strength)
        self._energies.append(energy)
        self._scores.append(score)
        self._attacks.append(energy)
        self._history.append((center, score, threshold))
        self.frame_id += 1
        self.latest = KickSnapshot(self.frame_id, self._origin + self._size / self._rate,
            db, attack, flux, contrast, low_fraction, score, threshold, regularity,
            self.count, ready, self._events[-1] if self._events else None,
            tuple(self._events), tuple(self._history), (cfg.kick_low_hz, cfg.kick_high_hz),
            self._size / self._rate * 1000, self._hop / self._rate * 1000)
