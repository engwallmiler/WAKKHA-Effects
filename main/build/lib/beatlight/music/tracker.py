"""Beat Tracker causal por hipóteses de intervalos e PLL de fase/período.

Não infere downbeat/compasso. Não altera nem realimenta o detector de kicks.
"""
from collections import deque
from dataclasses import replace
import math
import numpy as np
from beatlight.contracts import BeatSnapshot, KickEvent, TempoHypothesis
from beatlight.music.clock import project_clock
from beatlight.music.config import BeatConfig


class BeatTracker:
    def __init__(self, config: BeatConfig | None = None):
        self.config = config or BeatConfig()
        self.reset()

    def reset(self):
        self._last_seen = -math.inf
        self._now = -math.inf
        self._history = deque(maxlen=120)
        self._history_at = -math.inf
        self._clear_clock()

    def _clear_clock(self):
        self._events = deque(maxlen=32)
        self._period = None
        self._anchor = None
        self._anchor_index = 0
        self._reported_index = 0
        self._last_reference = None
        self._confidence = 0.0
        self._phase_error = 0.0
        self._hits = self._bad = 0
        self._matched = self._rejected = 0
        self._alternative = None
        self._alternative_hits = 0
        self._hypotheses = ()
        self._ambiguous = False

    def _fit(self, period):
        events = list(self._events)[-16:]
        times = np.array([e.occurred_at for e in events])
        weights = np.array([max(0.2, e.confidence) for e in events]) * 0.88 ** np.arange(len(events) - 1, -1, -1)
        # Testa âncoras recentes; grades em contratempos não recebem peso integral.
        anchors = times[-8:]
        distances = np.abs((times[None, :] - anchors[:, None] + period / 2) % period - period / 2) / period
        on = np.exp(-0.5 * (distances / 0.08) ** 2)
        off = np.exp(-0.5 * ((0.5 - distances) / 0.08) ** 2)
        quality = np.sum((on + 0.55 * off) * weights, axis=1) / np.sum(weights)
        best = int(np.argmax(quality))
        aligned = distances[best] < 0.14
        expected = max(1, round((times[-1] - times[0]) / period) + 1)
        occupancy = min(1.0, float(np.count_nonzero(aligned)) / expected)
        intervals = np.diff(times)
        direct = float(np.mean(np.exp(-0.5 * ((intervals / period - 1) / 0.08) ** 2))) if len(intervals) else 0.0
        score = float(np.clip(0.65 * quality[best] + 0.2 * occupancy + 0.15 * direct, 0, 1))
        return score, float(anchors[best])

    def _estimate(self):
        times = np.array([e.occurred_at for e in list(self._events)[-12:]])
        votes = {}
        cfg = self.config
        for lag in range(1, min(5, len(times))):
            for delta in (times[lag:] - times[:-lag]):
                for beats in (0.5, 1, 2, 3, 4):
                    bpm = 60 * beats / delta
                    if cfg.beat_min_bpm <= bpm <= cfg.beat_max_bpm:
                        key = min(cfg.beat_max_bpm, max(cfg.beat_min_bpm, round(bpm * 2) / 2))
                        votes[key] = votes.get(key, 0.0) + 1 / (lag * max(1, beats))
        candidates = sorted(votes, key=votes.get, reverse=True)[:16]
        if self._period:
            candidates.append(60 / self._period)
        if not candidates:
            return None
        scored = [(self._fit(60 / bpm)[0], bpm) for bpm in candidates]
        score, bpm = max(scored)
        return bpm, score, self._fit(60 / bpm)[1]

    def _update_hypotheses(self):
        if self._period is None:
            return
        cfg = self.config
        bpm = 60 / self._period
        self._hypotheses = tuple(TempoHypothesis(relation, bpm * factor,
            self._fit(self._period / factor)[0], cfg.beat_min_bpm <= bpm * factor <= cfg.beat_max_bpm)
            for relation, factor in (("half", 0.5), ("normal", 1.0), ("double", 2.0)))
        normal = self._hypotheses[1].score
        self._ambiguous = max(self._hypotheses[0].score, self._hypotheses[2].score) >= normal - 0.12

    def _acquire(self, bpm, score, anchor):
        self._period = 60 / bpm
        # A contagem inicia na primeira grade adquirida, sem atribuir compasso.
        self._anchor = anchor
        self._anchor_index = self._reported_index = 0
        self._last_reference = self._events[-1].occurred_at
        self._confidence = score * 0.55
        self._hits = self._bad = 0
        self._alternative_hits = 0

    def _observe(self, event):
        t = event.occurred_at
        self._events.append(event)
        while self._events and t - self._events[0].occurred_at > 12:
            self._events.popleft()
        estimate = self._estimate() if len(self._events) >= 4 else None
        if self._period is None:
            if estimate and estimate[1] >= 0.62:
                self._acquire(*estimate)
                self._update_hypotheses()
            return
        cycles = round((t - self._anchor) / self._period)
        error = t - (self._anchor + cycles * self._period)
        if cycles >= 1 and abs(error) <= self._period * 0.18:
            previous_period = self._period
            # Correção proporcional de fase e integral do período, sem reset por kick.
            self._anchor += cycles * previous_period + 0.28 * error
            self._anchor_index += cycles
            self._period = float(np.clip(previous_period + 0.07 * error / cycles,
                60 / self.config.beat_max_bpm, 60 / self.config.beat_min_bpm))
            self._phase_error = error * 1000
            self._last_reference = t
            quality = max(0, 1 - abs(error) / (previous_period * 0.18)) * event.confidence
            self._confidence = 0.85 * self._confidence + 0.15 * quality
            self._hits += 1
            self._bad = 0
            self._matched += 1
        else:
            self._rejected += 1
            # Um contratempo não apaga a estabilidade das batidas principais.
            if cycles >= 1 and t - self._last_reference > self._period * 0.8:
                self._bad += 1
                self._confidence *= 0.92
        if estimate:
            bpm, score, anchor = estimate
            difference = abs(bpm / (60 / self._period) - 1)
            current_score = self._fit(self._period)[0]
            if difference > 0.08 and score > current_score + 0.12:
                if self._alternative and abs(bpm / self._alternative - 1) < 0.03:
                    self._alternative_hits += 1
                else:
                    self._alternative, self._alternative_hits = bpm, 1
                if self._alternative_hits >= 3:
                    self._acquire(bpm, score, anchor)
            else:
                self._alternative_hits = 0
        self._update_hypotheses()

    def process(self, events: tuple[KickEvent, ...], at: float) -> BeatSnapshot:
        if not math.isfinite(at) or at < self._now:
            raise ValueError("Tempo do tracker deve avançar monotonamente.")
        self._now = at
        last_input = self._last_reference if self._period else self._events[-1].occurred_at if self._events else None
        if last_input is not None and at - last_input >= self.config.beat_hold_seconds:
            self._clear_clock()  # watermark é preservado para não reingerir eventos antigos
        for event in sorted(events, key=lambda e: e.occurred_at):
            if (not math.isfinite(event.occurred_at) or event.occurred_at > at
                    or event.occurred_at <= self._last_seen):
                continue
            self._last_seen = event.occurred_at
            if (not math.isfinite(event.confidence) or event.confidence < 0.25
                    or at - event.occurred_at >= self.config.beat_hold_seconds):
                continue
            self._observe(event)
        state = "acquiring" if self._events else "unlocked"
        phase = 0.0
        last = next_beat = None
        index = self._reported_index
        if self._period:
            cycles = (at - self._anchor) / self._period
            whole = math.floor(cycles + 1e-9)
            phase = max(0.0, min(1.0, cycles - whole))
            last = self._anchor + whole * self._period
            next_beat = last + self._period
            index = max(self._reported_index, self._anchor_index + whole)
            self._reported_index = index
            state = "locked" if self._hits >= 3 and self._confidence >= 0.6 and self._bad < 3 else "acquiring"
        reference_at = self._last_reference if self._last_reference is not None else self._events[-1].occurred_at if self._events else None
        effective_confidence = self._confidence * (0.8 if self._ambiguous else 1.0)
        snapshot = BeatSnapshot(at, state, 60 / self._period if self._period else 0.0,
            self._period or 0.0, phase, index, last, next_beat, reference_at,
            reference_at + self.config.beat_hold_seconds if reference_at is not None else None,
            effective_confidence, effective_confidence, self._phase_error, self._matched, self._rejected,
            self._hypotheses, self._ambiguous, tuple(self._history))
        snapshot = project_clock(snapshot, at)
        if at - self._history_at >= 0.25:
            self._history.append((at, snapshot.bpm, snapshot.confidence))
            self._history_at = at
        return replace(snapshot, history=tuple(self._history))
