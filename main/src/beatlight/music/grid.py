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
        self.seeds = deque(maxlen=16)
        self.recovery = deque(maxlen=4)
        self.candidates = deque(maxlen=4)
        self.jitter = 0.004
        self.period_error = 0.0
        self.rejected = 0
        self.phrase_origin = 0
        self.revision = self.corrections = 0
        self.last_correction_ms = 0.0
        self.tempo_locked=self.config.beat_grid_mode=='continuous'
        self.estimated_bpm=0.;self.tempo_changes=0
        self._tempo_vote=None;self._tempo_votes=0;self._tempo_cooldown=-math.inf

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
        if self.config.beat_grid_mode=='manual':return abs(60/period-self.config.beat_fixed_bpm)<=self.config.beat_fixed_bpm*.08
        return self.config.beat_min_bpm - 1e-6 <= 60 / period <= self.config.beat_max_bpm + 1e-6

    def _seed_sequence(self):
        """Quatro ataques reais regulares, mesmo com candidatos entre eles.

        Não cria observações previstas. O caminho consecutivo conserva a
        aquisição anterior; a busca limitada só atua antes da primeira grade.
        """
        events=list(self.seeds)
        direct=events[-4:];period=self._cadence(direct)
        if period is not None and self._in_range(period):return period,direct
        if len(events)<6:return None
        last=events[-1];best=None
        for previous in events[:-1]:
            for count in range(1,5):
                candidate=(last.occurred_at-previous.occurred_at)/count
                if not self._in_range(candidate):continue
                aligned={}
                for event in events:
                    n=round((event.occurred_at-last.occurred_at)/candidate)
                    error=abs(event.occurred_at-last.occurred_at-n*candidate)
                    if error>max(.008,candidate*.045):continue
                    if n not in aligned or error<aligned[n][0]:aligned[n]=(error,event)
                for start in sorted(aligned):
                    if not all(n in aligned for n in range(start,start+4)):continue
                    sequence=[aligned[n][1] for n in range(start,start+4)]
                    fitted=self._cadence(sequence)
                    if fitted is None or not self._in_range(fitted):continue
                    score=sum(aligned[n][0] for n in range(start,start+4))/candidate
                    if best is None or (score,sequence[0].occurred_at)<(best[0],best[2][0].occurred_at):best=(score,fitted,sequence)
        return (best[1],best[2]) if best else None

    def observe(self, event, beat=None):
        t = event.occurred_at
        if not math.isfinite(t):
            return
        if not self.ready:
            if self.seeds and t <= self.seeds[-1].occurred_at:
                return
            self.seeds.append(event)
            sequence=self._seed_sequence()
            if sequence is None:
                return
            period,events=sequence
            self.anchor, self.period = events[0].occurred_at, period
            self.observations.extend((i, e.occurred_at) for i, e in enumerate(events))
            self.last_reference = events[-1].occurred_at
            self.candidates.extend(events)
            self._fit(initial=True)
            return
        n = round((t - self.anchor) / self.period)
        if self.observations and n <= self.observations[-1][0]:
            return
        self.observations.append((n, t))
        self.last_reference = t
        self.recovery.clear()
        self._fit()

    def _fit(self,initial=False):
        xs, ys = zip(*self.observations)
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        variance = sum((x - mx) ** 2 for x in xs)
        fitted = sum((x - mx) * (y - my) for x, y in self.observations) / max(variance, 1)
        self.estimated_bpm=60/fitted if fitted>0 else 0.
        if self.config.beat_grid_mode!='continuous':
            self._fit_stable(fitted,mx,my,initial)
            residuals=[abs(y-(my+fitted*(x-mx))) for x,y in self.observations]
            self.jitter=max(.004,median(residuals)*1.48)
            self.period_error=max(self.period*.0001,self.jitter/math.sqrt(max(variance,1)))
            return
        if abs(fitted / self.period - 1) < 0.04:
            n, t = self.observations[-1]
            predicted = self.anchor + n * self.period
            if initial:
                self.period=fitted;self.anchor=my-fitted*mx
            else:
                self.period += (fitted - self.period) * 0.2
                # Preserva a posição atual ao corrigir período, inclusive após muitos compassos.
                self.anchor = predicted - n * self.period + (t - predicted) * 0.25
        residuals = [abs(y - (my + fitted * (x - mx))) for x, y in self.observations]
        self.jitter = max(0.004, median(residuals) * 1.48)
        self.period_error = max(self.period * 0.0001, self.jitter / math.sqrt(max(variance, 1)))

    def _integer_period(self,bpm):
        integer=max(math.ceil(self.config.beat_min_bpm),min(math.floor(self.config.beat_max_bpm),math.floor(bpm+.5)))
        return 60/integer

    def _robust_period(self):
        recent = list(self.observations)[-8:]
        slopes = [(yb-ya)/(xb-xa) for i,(xa,ya) in enumerate(recent)
            for xb,yb in recent[i+1:] if xb>xa]
        return median(slopes)

    def _fit_stable(self,fitted,mx,my,initial):
        n,t=self.observations[-1];old_target=self.anchor+n*self.period
        manual=self.config.beat_grid_mode=='manual'
        if not self.tempo_locked:
            if manual:
                self.period=60/self.config.beat_fixed_bpm;self.anchor=my-self.period*mx;self.tempo_locked=True
            elif len(self.observations)>=8:
                self.period=self._integer_period(60/self._robust_period());self.anchor=my-self.period*mx;self.tempo_locked=True
            elif abs(fitted/self.period-1)<.04:
                self.period=fitted;self.anchor=my-fitted*mx
            return
        if not manual and len(self.observations)>=8 and t>=self._tempo_cooldown:
            slope=self._robust_period()
            measured=60/slope if slope>0 else 0.;candidate=self._integer_period(measured) if measured else self.period
            if candidate!=self.period and abs(measured-60/self.period)>=.75:
                if candidate==self._tempo_vote:self._tempo_votes+=1
                else:self._tempo_vote=candidate;self._tempo_votes=1
                if self._tempo_votes>=4:
                    self.period=candidate;self.anchor=old_target-n*self.period
                    self._tempo_cooldown=t+6*self.period;self._tempo_votes=0
                    self.tempo_changes+=1;self.revision+=1
            else:self._tempo_vote=None;self._tempo_votes=0
        # Corrigir fase aos poucos; o ruído de um ataque não muda o andamento.
        error=t-(self.anchor+n*self.period)
        if abs(error)>max(.004,self.period*.02):
            self.anchor+=max(-self.period*.04,min(self.period*.04,error))*.2

    def reconcile(self, event, at, allow_correction=True, *, phase_only=False):
        """Somente candidatos aprovados pelo perfil podem propor correção.

        Um ataque isolado ou um roll não altera a grade. Quatro ataques regulares
        e ausência de referências alinhadas por três períodos confirmam a mudança.
        """
        matched = self.matches(event, at)
        if self.config.beat_grid_mode=='manual' and not matched:
            self.rejected+=1;return False
        if not allow_correction:
            self.recovery.clear()
            self.candidates.clear()
            if not matched:
                self.rejected += 1
            return matched
        if not self.candidates or event.occurred_at > self.candidates[-1].occurred_at:
            self.candidates.append(event)
        cadence = self._cadence(self.candidates)
        tempo_change = (not phase_only and cadence is not None and self._in_range(cadence)
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
            if phase_only:
                if abs(candidate/self.period-1)>.06:
                    return False
                candidate=self.period
            multiple = round(candidate / self.period)
            # Kicks omitidos não devem reduzir o BPM pela metade.
            if 1 <= multiple <= 4 and abs(candidate / (multiple * self.period) - 1) < 0.04:
                candidate = self.period
            if not self._in_range(candidate):
                return False
            references = tuple(self.recovery)
        n = round((event.occurred_at - self.anchor) / self.period)
        old_target = self.anchor + n * self.period
        # A volta de uma bassline no contratempo não desloca uma grade inteira
        # já estabilizada. Mudanças reais de andamento mantêm a recuperação de
        # quatro ataques; desvios menores podem corrigir a fase gradualmente.
        if (self.config.beat_grid_mode in ('integer', 'manual') and self.tempo_locked
                and not tempo_change and abs(event.occurred_at-old_target) > self.period*.3):
            self.recovery.clear()
            return False
        self.last_correction_ms = (event.occurred_at - old_target) * 1000
        old_period = self.period
        self.period = (self._integer_period(60/candidate) if self.tempo_locked and self.config.beat_grid_mode=='integer' else candidate)
        if self.config.beat_grid_mode=='manual':self.period=60/self.config.beat_fixed_bpm
        if self.config.beat_grid_mode=='integer' and self.tempo_locked and self.period!=old_period:
            self.tempo_changes += 1
            self._tempo_cooldown = event.occurred_at + 6*self.period
            self._tempo_vote = None
            self._tempo_votes = 0
        self.anchor = event.occurred_at - n * self.period
        self.observations.clear()
        for e in references:
            self.observations.append((round((e.occurred_at - self.anchor) / self.period), e.occurred_at))
        self.last_reference = event.occurred_at
        self.recovery.clear()
        self.revision += 1
        self.corrections += 1
        if phase_only:
            # Máximos e começos de ataque têm latências diferentes. Esta
            # recuperação calibra somente fase, nunca a estimativa de BPM.
            self.jitter=max(.004,median(abs(y-(self.anchor+x*self.period)) for x,y in self.observations))
        else:
            self._fit()
        return True

    def reset_phrase(self, at):
        if self.ready:
            self.phrase_origin = round((at - self.anchor) / self.period)

    def snapshot(self, at):
        if not self.ready:
            return KickGridSnapshot(at, "learning", self.period, confidence=0.0,
                rejected_offgrid=self.rejected, observations=len(self.seeds),tempo_mode=self.config.beat_grid_mode,tempo_locked=False)
        reference_confidence = max(0.6, 0.95 * (1 - min(0.35, self.jitter / (self.period * 0.22))))
        base = KickGridSnapshot(at, "tracking", self.period, self.anchor, reference_confidence,
            last_reference_at=self.last_reference, rejected_offgrid=self.rejected,
            phrase_origin=self.phrase_origin, revision=self.revision, corrections=self.corrections,
            last_correction_ms=self.last_correction_ms, observations=len(self.observations),
            jitter_ms=self.jitter * 1000, period_error_ms=self.period_error * 1000,
            reference_confidence=reference_confidence)
        base=replace(base,tempo_mode=self.config.beat_grid_mode,tempo_locked=self.tempo_locked,
            estimated_bpm=self.estimated_bpm,tempo_changes=self.tempo_changes)
        return project_grid(base, at)

    def matches(self, event, at):
        if not self.ready:
            return False
        error = abs((event.occurred_at - self.anchor + self.period / 2) % self.period - self.period / 2)
        # Ausência de kicks aumenta incerteza, não abre a janela até o contratempo.
        tolerance = min(self.period * 0.18, max(0.025, self.period * 0.1 + self.jitter))
        return error <= tolerance
