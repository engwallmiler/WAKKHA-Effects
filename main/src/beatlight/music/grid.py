"""Grade local contínua: quatro ataques adquirem; desvios consistentes corrigem.

A grade organiza tempo, nunca cria KickEvent. Silêncio/fonte/descontinuidade
pertencem ao ciclo de vida do StructureTracker; ausência de kick não a pausa.
"""
from collections import deque
from dataclasses import replace
import math
from statistics import median
from beatlight.contracts import BeatSnapshot, KickGridSnapshot
from beatlight.music.config import BeatConfig


def project_grid(grid: KickGridSnapshot, at: float) -> KickGridSnapshot:
    """Projeção pura compartilhada pela análise, interface e iluminação."""
    if not math.isfinite(at):
        raise ValueError("Tempo da grade deve ser finito.")
    at = max(at, grid.updated_at)
    if grid.state not in ("tracking", "predicting") or not grid.period or grid.anchor_at is None:
        return replace(grid, updated_at=at)
    cycles = (at - grid.anchor_at) / grid.period
    whole = math.floor(cycles + 1e-7)
    phase = max(0.0, min(1.0, cycles - whole))
    age = max(0.0, at - (grid.last_reference_at if grid.last_reference_at is not None else grid.updated_at))
    uncertainty = grid.jitter_ms + age / grid.period * grid.period_error_ms
    # Quatro observações bastam para seguir o relógio, mas não para garantir
    # precisão futura. A incerteza cresce; o relógio continua explicitamente estimado.
    confidence = max(0.4, grid.reference_confidence * math.exp(-age / 120))
    next_at = grid.anchor_at + (whole + 1) * grid.period
    phrase_index = whole - grid.phrase_origin
    phrase_at = grid.anchor_at + (grid.phrase_origin + (math.floor(phrase_index / 8) + 1) * 8) * grid.period
    return replace(grid, updated_at=at, state="tracking" if age < 1.7 * grid.period else "predicting",
        beat_index=whole, phase=phase, confidence=confidence, uncertainty_ms=uncertainty,
        next_kick_at=next_at, next_phrase_at=phrase_at, horizon_seconds=60.0,
        predictions=tuple(next_at + i * grid.period for i in range(8)),
        forecast_30_at=grid.anchor_at + math.ceil((at + 30 - grid.anchor_at) / grid.period - 1e-7) * grid.period)


def grid_clock(grid, at, fallback=None):
    """BeatSnapshot de leitura: relógio da grade, sem alterar o PLL diagnóstico."""
    if grid is None or grid.state not in ("tracking", "predicting"):
        return None
    grid = project_grid(grid, at)
    return BeatSnapshot(grid.updated_at, "locked" if grid.state == "tracking" else "coasting",
        60 / grid.period, grid.period, grid.phase, grid.beat_index,
        grid.anchor_at + grid.beat_index * grid.period, grid.next_kick_at,
        grid.last_reference_at, None, grid.confidence, grid.reference_confidence,
        grid.last_correction_ms, 0, grid.rejected_offgrid,
        fallback.hypotheses if fallback else (), fallback.ambiguous if fallback else False,
        fallback.history if fallback else ())


class KickGrid:
    def __init__(self, config: BeatConfig | None = None):
        self.config = config or BeatConfig()
        self.anchor = None
        self.period = 0.0
        self.last_reference = None
        self.observations = deque(maxlen=32)
        self.seeds = deque(maxlen=4)
        self.recovery = deque(maxlen=4)
        self.candidates = deque(maxlen=4)
        self.jitter = 0.004
        self.period_error = 0.0
        self.rejected = 0
        self.phrase_origin = 0
        self.revision = self.corrections = 0
        self.last_correction_ms = 0.0

    @property
    def ready(self):
        return len(self.observations) >= 4

    def _cadence(self, events):
        if len(events) < 4:
            return None
        intervals = [b.occurred_at - a.occurred_at for a, b in zip(events, list(events)[1:])]
        period = median(intervals)
        if period <= 0 or max(abs(i - period) for i in intervals) > period * 0.06:
            return None
        return period

    def _in_range(self, period):
        return self.config.beat_min_bpm - 1e-6 <= 60 / period <= self.config.beat_max_bpm + 1e-6

    def observe(self, event, beat=None):
        t = event.occurred_at
        if not math.isfinite(t):
            return
        if not self.ready:
            if self.seeds and t <= self.seeds[-1].occurred_at:
                return
            self.seeds.append(event)
            period = self._cadence(self.seeds)
            if period is None or not self._in_range(period):
                return
            self.anchor, self.period = self.seeds[0].occurred_at, period
            self.observations.extend((i, e.occurred_at) for i, e in enumerate(self.seeds))
            self.last_reference = t
            self.candidates.extend(self.seeds)
            self._fit()
            return
        n = round((t - self.anchor) / self.period)
        if self.observations and n <= self.observations[-1][0]:
            return
        self.observations.append((n, t))
        self.last_reference = t
        self.recovery.clear()
        self._fit()

    def _fit(self):
        xs, ys = zip(*self.observations)
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        variance = sum((x - mx) ** 2 for x in xs)
        fitted = sum((x - mx) * (y - my) for x, y in self.observations) / max(variance, 1)
        if abs(fitted / self.period - 1) < 0.04:
            n, t = self.observations[-1]
            predicted = self.anchor + n * self.period
            self.period += (fitted - self.period) * 0.2
            # Preserva a posição atual ao corrigir período, inclusive após muitos compassos.
            self.anchor = predicted - n * self.period + (t - predicted) * 0.25
        residuals = [abs(y - (my + fitted * (x - mx))) for x, y in self.observations]
        self.jitter = max(0.004, median(residuals) * 1.48)
        self.period_error = max(self.period * 0.0001, self.jitter / math.sqrt(max(variance, 1)))

    def reconcile(self, event, at, allow_correction=True):
        """Somente candidatos aprovados pelo perfil podem propor correção.

        Um ataque isolado ou um roll não altera a grade. Quatro ataques regulares
        e ausência de referências alinhadas por três períodos confirmam a mudança.
        """
        matched = self.matches(event, at)
        if not allow_correction:
            self.recovery.clear()
            self.candidates.clear()
            if not matched:
                self.rejected += 1
            return matched
        if not self.candidates or event.occurred_at > self.candidates[-1].occurred_at:
            self.candidates.append(event)
        cadence = self._cadence(self.candidates)
        tempo_change = (cadence is not None and self._in_range(cadence)
            and abs(cadence / self.period - 1) > 0.04
            and not (2 <= round(cadence / self.period) <= 4
                and abs(cadence / (round(cadence / self.period) * self.period) - 1) < 0.04))
        if tempo_change:
            candidate, references = cadence, tuple(self.candidates)
        else:
            if matched:
                self.recovery.clear()
                return True
            self.rejected += 1
            if self.recovery and event.occurred_at <= self.recovery[-1].occurred_at:
                return False
            self.recovery.append(event)
            candidate = self._cadence(self.recovery)
            if candidate is None or at - self.last_reference < 3 * self.period:
                return False
            multiple = round(candidate / self.period)
            # Kicks omitidos não devem reduzir o BPM pela metade.
            if 1 <= multiple <= 4 and abs(candidate / (multiple * self.period) - 1) < 0.04:
                candidate = self.period
            if not self._in_range(candidate):
                return False
            references = tuple(self.recovery)
        n = round((event.occurred_at - self.anchor) / self.period)
        old_target = self.anchor + n * self.period
        self.last_correction_ms = (event.occurred_at - old_target) * 1000
        self.period = candidate
        self.anchor = event.occurred_at - n * candidate
        self.observations.clear()
        for e in references:
            self.observations.append((round((e.occurred_at - self.anchor) / candidate), e.occurred_at))
        self.last_reference = event.occurred_at
        self.recovery.clear()
        self.revision += 1
        self.corrections += 1
        self._fit()
        return True

    def reset_phrase(self, at):
        if self.ready:
            self.phrase_origin = round((at - self.anchor) / self.period)

    def snapshot(self, at):
        if not self.ready:
            return KickGridSnapshot(at, "learning", self.period, confidence=0.0,
                rejected_offgrid=self.rejected, observations=len(self.seeds))
        reference_confidence = max(0.6, 0.95 * (1 - min(0.35, self.jitter / (self.period * 0.22))))
        base = KickGridSnapshot(at, "tracking", self.period, self.anchor, reference_confidence,
            last_reference_at=self.last_reference, rejected_offgrid=self.rejected,
            phrase_origin=self.phrase_origin, revision=self.revision, corrections=self.corrections,
            last_correction_ms=self.last_correction_ms, observations=len(self.observations),
            jitter_ms=self.jitter * 1000, period_error_ms=self.period_error * 1000,
            reference_confidence=reference_confidence)
        return project_grid(base, at)

    def matches(self, event, at):
        if not self.ready:
            return False
        error = abs((event.occurred_at - self.anchor + self.period / 2) % self.period - self.period / 2)
        # Ausência de kicks aumenta incerteza, não abre a janela até o contratempo.
        tolerance = min(self.period * 0.18, max(0.025, self.period * 0.1 + self.jitter))
        return error <= tolerance
