"""Evidências causais de retorno: potência física, pausa e cadência do build.

Nenhuma previsão de batida vira kick. A identidade estrita e a grade continuam
sendo verificadas pelo StructureTracker antes de autorizar o drop.
"""
from collections import deque
import math
from statistics import median
from beatlight.contracts import DropEvidenceSnapshot


class DropDetector:
    MIN_POWER_RATIO = .70
    FAST_POWER_RATIO = .85

    def __init__(self):
        self.powers = deque(maxlen=16)
        self.highs = deque(maxlen=16)
        self.reference_db = None
        self.rms_history = deque(maxlen=100)
        self.quiet_since = None
        self.last_quiet = None
        self.pause_until = -math.inf
        self.candidate_times = deque(maxlen=8)
        self.candidate_db = None
        self.candidate_at = -math.inf
        self.candidate_gap_beats = 0.0
        self.power_ratio = 0.0
        self.accelerated = False
        self.high_return = False
        self.rejected_weak = 0
        self.weak_at = -math.inf
        self.reason = ""
        self.confirmation_ms = None
        self.fast_confirmed = False
        self.rescued_attack = False

    def learn(self, descriptor):
        if descriptor is None or descriptor.power_db <= -100:
            return
        self.powers.append(10 ** (descriptor.power_db / 10))
        self.highs.append(descriptor.peak_high_db)
        # Média em potência linear. Aparar extremos limita acentos isolados.
        values = sorted(self.powers)
        if len(values) >= 8:
            values = values[1:-1]
        self.reference_db = 10 * math.log10(sum(values) / len(values))

    @property
    def ready(self):
        return len(self.powers) >= 4

    def observe(self, feature, context, period):
        at = feature.at
        previous = [db for t, db in self.rms_history if .12 <= at - t <= 1.5]
        valley = context and (feature.rms_db < -60 or
            previous and median(previous) - feature.rms_db >= 8)
        if valley:
            self.quiet_since = at if self.quiet_since is None else self.quiet_since
            self.last_quiet = at
            if .06 <= at - self.quiet_since <= 1.5:
                self.pause_until = at + max(.5, min(1.0, 2 * period))
        else:
            self.quiet_since = None
        if not self.rms_history or at - self.rms_history[-1][0] >= .04:
            self.rms_history.append((at, feature.rms_db))

    def pause_recent(self, at):
        return self.last_quiet is not None and self.last_quiet <= at <= self.pause_until

    def fast_return(self, at, period, last_kick):
        missing = (at - last_kick) / period if last_kick is not None and period else 0
        return self.ready and (missing >= 7.5 or self.pause_recent(at))

    def strong_candidate(self, event, descriptor, period, last_kick=None):
        self.candidate_at = event.occurred_at
        self.candidate_gap_beats = max(0.0, (event.occurred_at-last_kick)/period) if last_kick is not None and period else 0.0
        self.candidate_times.append(event.occurred_at)
        times = [t for t in self.candidate_times if event.occurred_at - t <= 2 * period]
        intervals = [b - a for a, b in zip(times, times[1:])]
        self.accelerated = bool(period and len(intervals) >= 2 and
            sum(.30 * period <= gap <= .68 * period for gap in intervals[-3:]) >= 2)
        if descriptor is None or not self.ready:
            # Compatibilidade de descritores legados: mantém a recuperação antiga.
            return True
        self.candidate_db = descriptor.power_db
        self.power_ratio = 10 ** ((descriptor.power_db - self.reference_db) / 10)
        self.high_return = bool(self.highs and descriptor.peak_high_db >= median(self.highs) - 6)
        reinforced = self.high_return or self.pause_recent(event.occurred_at)
        threshold = self.FAST_POWER_RATIO if self.accelerated or not reinforced else self.MIN_POWER_RATIO
        if self.power_ratio < threshold:
            self.rejected_weak += 1
            self.weak_at = event.occurred_at
            self.reason = ("Kick acelerado do build" if self.accelerated else "Retorno de kick fraco") + f": {self.power_ratio:.0%} da potência de referência."
            return False
        self.reason = f"Retorno forte: {self.power_ratio:.0%} da potência do groove."
        return True

    @staticmethod
    def recovered(descriptor, low, current_low, low_ref, break_low):
        # O pico do próprio ataque não espera a média de 600 ms recuperar.
        peak = descriptor.peak_low_db if descriptor is not None else -120
        returned = max(low, current_low, peak)
        # Um transiente separado do fundo, validado em timbre e potência,
        # também prova o retorno quando o baixo já sustentava a mixagem.
        return returned > low_ref - 4 and (returned - break_low >= 7
            or descriptor is not None and descriptor.early)

    def confirm(self,event,descriptor,at):
        self.confirmation_ms = max(0.0,(at-event.occurred_at)*1000)
        self.fast_confirmed = bool(descriptor and descriptor.early)
        self.rescued_attack = bool(descriptor and descriptor.rescued)

    def snapshot(self, at, period, last_kick, armed):
        missing = max(0.0, (at - last_kick) / period) if last_kick is not None and period else 0.0
        if not armed and at - self.candidate_at < .8:
            missing = self.candidate_gap_beats
        pause = self.pause_recent(at)
        reason = self.reason if at - self.candidate_at < .8 else (
            "Pausa antes do impacto; aguardando kick forte." if armed and pause else
            f"Retorno armado após {missing:.0f} tempos sem kick forte." if armed and missing >= 7.5 else "")
        return DropEvidenceSnapshot(self.reference_db, self.candidate_db,
            self.power_ratio, missing, armed, pause, self.accelerated,
            self.high_return, self.rejected_weak, reason,self.confirmation_ms,
            self.fast_confirmed,self.rescued_attack)
