"""Máquina causal de estrutura: descritores, kicks e último período confiável.

Heurística conservadora; não reconhece instrumentos nem a métrica real. Frases
relativas de oito tempos assumem 4/4. Nenhuma dependência de áudio, Qt ou luz.
"""
from collections import deque
import math
from statistics import median
from beatlight.contracts import MusicalEvent, StructureFeatures, StructureSnapshot
from beatlight.music.grid import KickGrid
from beatlight.music.config import BeatConfig
from beatlight.music.kick_identity import KickIdentity
from beatlight.music.drop import DropDetector


def clamp(value, low=0.0, high=1.0):
    return min(high, max(low, value))


def mean_db(values):
    return 10 * math.log10(max(1e-12, sum(10 ** (v / 10) for v in values) / len(values)))


class StructureTracker:
    DROP_KICKS = 8

    def __init__(self, config: BeatConfig | None = None):
        self.config = config or BeatConfig()
        self.reset()

    def reset(self):
        self._grid = KickGrid(self.config)
        self._identity = KickIdentity()
        self._drop_detector = DropDetector()
        self._pause_state = None
        self._pending_descriptor = None
        self._confirmed = deque(maxlen=16)
        self._acoustic = deque(maxlen=16)
        self._at = None
        self._cursor = -math.inf
        self._last_kick = None
        self._first_kick = None
        self._kick_count = 0
        self._phrase_count = 0
        self._period = 0.0
        self._state = "warming"
        self._history = deque(maxlen=80)  # 4 s a 20 Hz
        self._onsets = deque(maxlen=96)
        self._percussion_onsets = deque(maxlen=128)
        self._groove_rate = 0.0
        self._groove_roll_rate = 0.0
        self._groove_percussion = -120.0
        self._roll_candidate_at = None
        self._last_roll_at = -math.inf
        self._return_armed = False
        self._sample_at = -math.inf
        self._low_ref = None
        self._rms_ref = None
        self._break_at = None
        self._break_low = -120.0
        self._break_high = -120.0
        self._break_rate = 0.5
        self._break_brightness = 0.0
        self._tension = 0.0
        self._drop_id = 0
        self._drop_at = None
        self._drop_count = 0
        self._events = deque(maxlen=24)
        self._pending_kick = None
        self._quiet_at = None
        self._learned = False
        self._rejected_returns = 0
        self._context_at = None
        self._context_candidate = None
        self._context_candidate_at = None

    def _clear_reference(self):
        self._learned = False
        self._context_at = None
        self._context_candidate = None
        self._history.clear()
        self._onsets.clear()
        self._percussion_onsets.clear()
        self._grid = KickGrid(self.config)
        self._identity = KickIdentity()
        self._confirmed.clear()
        self._acoustic.clear()
        self._last_kick = None
        self._cursor = -math.inf
        self._first_kick = None
        self._kick_count = self._phrase_count = 0
        self._break_at = None
        self._pending_kick = None
        self._drop_count = 0
        self._low_ref = self._rms_ref = None
        self._drop_detector = DropDetector()
        self._pause_state = None
        self._pending_descriptor = None
        self._return_armed = False
        self._roll_candidate_at = None
        self._last_roll_at = -math.inf

    def _pause_limit(self):
        return max(.8, min(1.5, 2.5 * self._period))

    def _change(self, state, at, confidence, intensity):
        if state != self._state:
            self._state = state
            self._events.append(MusicalEvent(state, at, confidence, intensity))

    def _initial_context(self, feature, recent, low, rms, rate, regular, roll_rate, roll_regular, at):
        """Contexto provisório não depende de quatro kicks; nunca autoriza drop."""
        if feature.rms_db >= -60:
            self._context_at = at if self._context_at is None else self._context_at
        else:
            self._context_at = None
        ready = self._context_at is not None and at - self._context_at >= 1.2 and len(self._history) >= 12
        seed = f"Grade acústica: {min(4, len(self._grid.seeds))}/4 ataques regulares; faixa {self.config.beat_min_bpm:g}–{self.config.beat_max_bpm:g} BPM."
        if not ready:
            self._change("warming", at, 0.0, 0.0)
            return "Analisando o contexto inicial (1,2 s de áudio). " + seed, 0.0, 0.0
        older = [f for f in self._history if .8 <= at - f.at <= 2.5]
        rise = (mean_db([f.high_db for f in recent]) - mean_db([f.high_db for f in older])) if older else 0.0
        brightening = (feature.brightness - sum(f.brightness for f in older) / len(older)) if older else 0.0
        # Um hi-hat estável rápido não basta: precisa também de crescimento.
        building = ((roll_regular and roll_rate >= 4.5 or regular and rate >= 5)
                    and (rise >= 2.5 or brightening >= .08))
        recent_kick = self._last_kick is not None and at - self._last_kick < max(1.1, self._period * 2.2)
        rhythmic = recent_kick or regular and rate >= 1 and low > rms - 18
        candidate = "buildup" if building else "groove" if rhythmic else "breakdown"
        if candidate != self._context_candidate:
            self._context_candidate, self._context_candidate_at = candidate, at
        if self._state in ("warming", "silence") or at - self._context_candidate_at >= .65:
            self._change(candidate, at, .55, .3 if building else 0.0)
        state = self._state
        target = .5 if state == "buildup" else .08 if state == "breakdown" else 0.0
        description = {"groove": "Groove provável: atividade rítmica e graves presentes.",
            "breakdown": "Breakdown/intro provável: trecho sem kick regular, com pouca atividade rítmica.",
            "buildup": "Build-up provável: ataques rápidos e crescimento espectral."}[state]
        return description + " Contexto provisório; perfil do kick ainda em aquisição. " + seed, .55, target

    def process(self, feature: StructureFeatures, kicks=(), beat=None) -> StructureSnapshot:
        at = feature.at
        if not math.isfinite(at) or self._at is not None and at < self._at:
            raise ValueError("Descritores estruturais devem avançar monotonamente.")
        if not all(math.isfinite(v) for v in (feature.low_db, feature.high_db, feature.rms_db, feature.brightness)):
            raise ValueError("Descritores estruturais inválidos.")
        if self._at is not None and at - self._at > 0.75:
            self.reset()
        dt = min(0.2, at - self._at) if self._at is not None else 0.01
        self._at = at
        if beat and beat.state == "locked" and beat.confidence >= 0.45 and 0.25 <= beat.period <= 1.2:
            self._period = beat.period
        if self._grid.ready:
            self._period = self._grid.period
        if feature.onset:
            self._onsets.append(at)
        if feature.percussion_onset:
            self._percussion_onsets.append(at)
        while self._percussion_onsets and self._percussion_onsets[0] < at - 4:
            self._percussion_onsets.popleft()
        while self._onsets and self._onsets[0] < at - 4:
            self._onsets.popleft()
        if at - self._sample_at >= 0.045:
            self._history.append(feature)
            self._sample_at = at
        recent = [f for f in self._history if f.at >= at - 0.6] or [feature]
        low = mean_db([f.low_db for f in recent])
        high = mean_db([f.high_db for f in recent])
        rms = mean_db([f.rms_db for f in recent])
        brightness = sum(f.brightness for f in recent) / len(recent)
        percussion = mean_db([f.percussion_db for f in recent])
        recent_onsets = [t for t in self._onsets if t >= at - 2]
        intervals = [b - a for a, b in zip(recent_onsets, recent_onsets[1:])]
        rate = 1 / median(intervals[-8:]) if len(intervals) >= 3 else 0.0
        regular = bool(len(intervals) >= 3 and median(abs(i - median(intervals)) for i in intervals) < 0.45 * median(intervals))
        roll_times = [t for t in self._percussion_onsets if t >= at - 2.5]
        roll_intervals = [b - a for a, b in zip(roll_times, roll_times[1:])]
        roll_period = median(roll_intervals[-12:]) if len(roll_intervals) >= 4 else 0.0
        roll_rate = 1 / roll_period if roll_period else 0.0
        roll_regular = bool(roll_period and roll_times[-1] - roll_times[0] >= 0.4
            and at - roll_times[-1] < max(0.22, roll_period * 2.3)
            and median(abs(i - roll_period) for i in roll_intervals[-12:]) < roll_period * 0.35)
        # Um apagão sonoro breve não apaga o kick aprendido antes do impacto.
        if self._pause_state is not None and feature.rms_db >= -60:
            previous = self._pause_state
            self._pause_state = None
            if self._quiet_at is not None and at - self._quiet_at <= self._pause_limit():
                self._change(previous, at, .75, self._tension)
            else:
                self._clear_reference()
        returning = self._learned and (self._state in ("breakdown", "buildup") or self._pause_state is not None)
        if feature.rms_db < -60 and returning and self._pause_state is None:
            self._pause_state = self._state
        self._drop_detector.observe(feature, returning, self._period)
        gap_before = at - self._last_kick if self._last_kick is not None else 0.0
        if self._state in ("breakdown", "buildup") and gap_before > max(1.1, 2.2 * self._period):
            self._return_armed = True
        new_kicks = []
        fast_return = returning and self._return_armed and self._drop_detector.fast_return(at, self._period, self._last_kick)
        after_pause = returning and self._drop_detector.pause_recent(at)
        for event in self._identity.push(feature, kicks, fast_return=fast_return, after_pause=after_pause,
                early_matches=lambda candidate: self._grid.matches(candidate, at)):
            self._acoustic.append(event)
            if event.occurred_at > at or event.occurred_at <= self._cursor:
                self._identity.discard(event)
                continue
            self._cursor = event.occurred_at
            if event.confidence < 0.35:
                self._identity.discard(event)
                continue
            descriptor = self._identity.descriptor(event)
            strict_return = self._identity.return_matches(event)
            if returning and not strict_return and after_pause:
                strict_return = self._identity.return_matches(event, after_pause=True)
            if returning and not strict_return:
                self._rejected_returns += 1
                self._identity.discard(event)
                continue
            if returning and not self._drop_detector.strong_candidate(event, descriptor, self._period, self._last_kick):
                self._rejected_returns += 1
                self._identity.discard(event)
                continue
            if self._grid.ready and not self._grid.reconcile(event, at, self._identity.correction_matches(event)):
                self._identity.discard(event)
                continue
            if self._last_kick is not None and event.occurred_at - self._last_kick < max(0.22, self._period * 0.55):
                self._identity.discard(event)
                continue
            learn = not self._learned or self._state in ("warming", "groove")
            if learn and (len(self._identity.references) < 4 or self._identity.return_matches(event)):
                self._drop_detector.learn(descriptor)
            self._identity.accept(event, learn)
            if learn or self._state == "drop":
                self._grid.observe(event, beat)
            self._confirmed.append(event)
            self._last_kick = event.occurred_at
            self._pending_kick = event
            self._pending_descriptor = descriptor
            self._first_kick = self._first_kick if self._first_kick is not None else event.occurred_at
            self._kick_count += 1
            self._phrase_count += 1
            new_kicks.append(event)
        if self._grid.ready:
            self._period = self._grid.period
        gap = at - self._last_kick if self._last_kick is not None else 0.0
        if feature.rms_db < -60:
            self._quiet_at = at if self._quiet_at is None else self._quiet_at
        else:
            self._quiet_at = None
        quiet = self._quiet_at is not None and at - self._quiet_at > 0.35
        if quiet:
            preserve = self._pause_state is not None and at - self._quiet_at <= self._pause_limit()
            if not preserve:
                self._clear_reference()
            self._change("silence", at, 0.9, 0.0)
            reason = ("Pausa antes do drop; referência do groove preservada por um instante."
                      if preserve else "Silêncio; aguardando um novo groove para aprender a referência.")
            confidence, target = 0.9, 0.0
        else:
            if (not self._learned and self._grid.ready and self._kick_count >= 4
                    and gap < self._period * 1.7):
                self._learned = True
                self._low_ref, self._rms_ref = low, rms
                self._groove_rate, self._groove_roll_rate = rate, roll_rate
                self._groove_percussion = percussion
                self._break_at = None
                self._return_armed = False
                self._change("groove", at, 0.7, 0.0)
            if not self._learned:
                reason, confidence, target = self._initial_context(
                    feature, recent, low, rms, rate, regular, roll_rate, roll_regular, at)
            else:
                suppression = self._low_ref - low
                absent = gap > max(1.1, 2.2 * self._period)
                fast_roll = bool(roll_regular and roll_rate >= max(4.5, 2.25 / self._period)
                    and roll_rate > max(self._groove_roll_rate * 1.4, self._groove_roll_rate + 1.5)
                    and (absent or suppression >= 2 or percussion > self._groove_percussion + 1.5))
                general_roll = bool(absent and regular and rate >= max(5.0, 2.5 / self._period)
                    and rate > max(self._groove_rate * 1.4, self._groove_rate + 1.5))
                if fast_roll or general_roll:
                    self._roll_candidate_at = at if self._roll_candidate_at is None else self._roll_candidate_at
                    self._last_roll_at = at
                else:
                    self._roll_candidate_at = None
                sustained_roll = self._roll_candidate_at is not None and at - self._roll_candidate_at >= 0.35
                if self._state == "drop":
                    self._drop_count += len(new_kicks)
                    # Falha pontual de confirmação não encerra a cena antes de oito
                    # kicks. Uma retirada real exige também queda sustentada dos graves.
                    withdrawn = gap > max(1.5, 3 * self._period) and suppression >= 7
                    ended = self._drop_count > self.DROP_KICKS or withdrawn
                    if ended:
                        self._drop_count = 0
                        self._break_at = None
                        self._change("groove", at, 0.7, 0.0)
                if self._state == "groove" and sustained_roll and fast_roll and rms > -55:
                    self._break_at, self._break_low, self._break_high = at, low, high
                    self._break_rate = max(0.5, self._groove_rate)
                    self._break_brightness = brightness
                    self._pending_kick = None
                    self._return_armed = absent
                    self._change("buildup", at, 0.8, self._tension)
                if self._state in ("groove", "warming", "silence") and absent and suppression >= 5 and rms > -55:
                    self._break_at, self._break_low, self._break_high = at, low, high
                    self._break_rate = max(0.5, rate)
                    self._break_brightness = brightness
                    self._pending_kick = None
                    self._return_armed = True
                    self._change("breakdown", at, 0.7, 0.2)
                if self._state in ("breakdown", "buildup"):
                    self._break_low = min(self._break_low, low)
                    elapsed = at - self._break_at
                    rise = max(0.0, high - self._break_high)
                    acceleration = rate / self._break_rate if regular else 1.0
                    # Som crescendo ou ataques acelerando, além da ausência de kick.
                    brightening = max(0.0, brightness - self._break_brightness)
                    building = sustained_roll or (elapsed > 0.5 and regular
                        and (rise > 2.5 or acceleration > 1.35 or brightening > 0.08))
                    if building:
                        self._change("buildup", at, 0.8, self._tension)
                    pending = self._pending_kick
                    recovered = self._drop_detector.recovered(self._pending_descriptor,
                        low, feature.low_db, self._low_ref, self._break_low)
                    if (self._return_armed and pending and 0 <= at - pending.occurred_at < 0.25
                            and self._grid.matches(pending, at) and recovered):
                        self._grid.observe(pending, beat)
                        self._drop_id += 1
                        self._drop_at = pending.occurred_at
                        self._drop_count = self._phrase_count = 1
                        self._grid.reset_phrase(pending.occurred_at)
                        self._break_at = None
                        self._change("drop", at, 0.85, 1.0)
                    elif (gap < self._period * 1.5 and elapsed > 2 and suppression < 3
                          and at - self._last_roll_at > 0.8):
                        self._break_at = None
                        self._change("groove", at, 0.5, 0.0)
                if self._state == "drop":
                    target, confidence = 1.0, 0.85
                    reason = f"Retorno do kick e dos graves; alta energia no kick {self._drop_count}/8."
                elif self._state in ("breakdown", "buildup"):
                    rise = max(0.0, high - self._break_high)
                    acceleration = max(0.0, rate / self._break_rate - 1) if regular else 0.0
                    brightening = max(0.0, brightness - self._break_brightness)
                    roll_energy = (clamp((max(roll_rate, rate if general_roll else 0) * self._period - 1) / 6)
                                   if sustained_roll else 0.0)
                    evidence = roll_energy * 0.5 + clamp(rise / 12) * 0.45 + clamp(acceleration / 3) * 0.35 + clamp(brightening / 0.3) * 0.15
                    target = clamp(0.18 + evidence + min(0.1, (at - self._break_at) / 200), 0.15, 0.95)
                    confidence = clamp(0.55 + clamp(suppression / 15) * 0.25 + (0.1 if regular else 0))
                    reason = (("Build-up: roll rápido e sustentado de percussão." if fast_roll or general_roll
                               else "Build-up: ataques repetidos com aceleração ou crescimento dos agudos.") if self._state == "buildup"
                              else "Breakdown: ausência de kicks e redução dos graves; procurando sinais de tensão.")
                else:
                    target, confidence = 0.0, 0.7 if self._learned else 0.0
                    reason = "Groove; frase contínua de oito tempos na grade, assumindo 4/4." if self._learned else "Reaprendendo a referência musical."
                    if self._learned and gap < self._period * 1.7:
                        amount = 1 - math.exp(-max(0.0, dt) / 8)
                        self._low_ref += (low - self._low_ref) * amount
                        self._rms_ref += (rms - self._rms_ref) * amount
                        self._groove_rate += (rate - self._groove_rate) * amount
                        self._groove_roll_rate += (roll_rate - self._groove_roll_rate) * amount
                        self._groove_percussion += (percussion - self._groove_percussion) * amount
        self._tension += (target - self._tension) * (1 - math.exp(-max(dt, 0) / 0.4))
        if self._state == "drop":
            self._tension = 1.0
        energy = clamp((rms - (self._rms_ref or -25) + 12) / 24) if self._learned else clamp((rms + 60) / 45)
        evidence = self._drop_detector.snapshot(at, self._period, self._last_kick,
            self._learned and self._return_armed and (self._state in ("breakdown", "buildup") or self._pause_state is not None))
        if self._state in ("breakdown", "buildup") and evidence.reason:
            reason += " " + evidence.reason
        grid = self._grid.snapshot(at)
        phrase = (grid.beat_index - grid.phrase_origin) % 8 + 1 if self._grid.ready else 0
        return StructureSnapshot(at, self._state, clamp(self._tension), confidence, energy,
            clamp(brightness), rate, max(0.0, gap), phrase, (phrase - 1) % 4 + 1 if phrase else 0,
            (phrase - 1) // 4 + 1 if phrase else 0, self._drop_count, self._drop_id, self._drop_at,
            self._last_kick, self._period, reason, tuple(self._events), roll_rate,
            clamp((roll_rate * self._period - 1) / 6) if roll_regular and self._period else 0.0,
            grid, self._identity.rejected, self._identity.similarity, tuple(self._confirmed) if self._grid.ready else (), tuple(self._acoustic), self._rejected_returns, self._learned, drop_evidence=evidence)
