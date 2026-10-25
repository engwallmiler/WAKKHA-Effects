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
        self.peak_powers = deque(maxlen=16)
        self.highs = deque(maxlen=16)
        self.reference_db = None
        self.reference_peak_db = None
        self.peak_ratio = 0.0
        self.mean_reached = False
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
        self.spectral_flux = self.spectral_novelty = self.score = 0.0
        self.phase = "idle"
        self.continuation_count = 0
        self.continuation_deadline = -math.inf
        self.rejected_impacts = 0

    def full_power(self,descriptor):
        return descriptor is None or not self.ready or descriptor.power_db>=self.reference_db+10*math.log10(self.MIN_POWER_RATIO)

    def learn(self, descriptor):
        if descriptor is None or descriptor.power_db <= -100:
            return
        self.powers.append(10 ** (descriptor.power_db / 10))
        if descriptor.peak_low_db > -100:
            self.peak_powers.append(10 ** (descriptor.peak_low_db / 10))
            self.reference_peak_db = self._mean_db(self.peak_powers)
        self.highs.append(descriptor.peak_high_db)
        # Média em potência linear. Aparar extremos limita acentos isolados.
        self.reference_db = self._mean_db(self.powers)

    @staticmethod
    def _mean_db(powers):
        values = sorted(powers)
        if len(values) >= 8:
            values = values[1:-1]
        return 10 * math.log10(sum(values) / len(values))

    def reaches_groove_mean(self, descriptor):
        """Potência do transiente E pico, nunca somente a energia da bassline.

        A tolerância de 10%/15% evita exigir igualdade numérica entre ataques.
        Chamado após identidade/grade; não gera um kick ou arma contexto.
        """
        return bool(descriptor is not None and self.ready and len(self.peak_powers) >= 4
            and descriptor.power_db >= self.reference_db + 10 * math.log10(.90)
            and descriptor.peak_low_db >= self.reference_peak_db + 10 * math.log10(.85))

    @property
    def ready(self):
        return len(self.powers) >= 4

    def observe(self, feature, context, period):
        at = feature.at
        self.spectral_flux = max(0.0,min(1.0,feature.spectral_flux))
        self.spectral_novelty = max(0.0,min(1.0,feature.spectral_novelty))
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

    def observe_candidate(self,event,period):
        if not self.candidate_times or event.occurred_at>self.candidate_times[-1]:
            self.candidate_times.append(event.occurred_at)
        self._cadence(event.occurred_at,period)

    def observe_candidates(self,events,period,at):
        # Snapshots repeat their recent history. Append only new candidates and
        # analyze the latest cadence once, instead of replaying it 16 times/FFT.
        latest=None
        for event in events:
            if event.confidence<.35 or event.occurred_at>at:continue
            latest=event.occurred_at
            if not self.candidate_times or latest>self.candidate_times[-1]:self.candidate_times.append(latest)
        if latest is not None:self._cadence(latest,period)

    def _cadence(self,at,period):
        times=[t for t in self.candidate_times if 0<=at-t<=2*period]
        intervals=[b-a for a,b in zip(times,times[1:])]
        self.accelerated=bool(period and len(intervals)>=2 and
            sum(.30*period<=gap<=.68*period for gap in intervals[-3:])>=2)

    def strong_candidate(self, event, descriptor, period, last_kick=None):
        self.candidate_at = event.occurred_at
        self.candidate_gap_beats = max(0.0, (event.occurred_at-last_kick)/period) if last_kick is not None and period else 0.0
        self.observe_candidate(event,period)
        self.mean_reached = self.reaches_groove_mean(descriptor)
        self.peak_ratio = (10 ** ((descriptor.peak_low_db-self.reference_peak_db)/10)
                           if descriptor is not None and self.reference_peak_db is not None else 0.0)
        if descriptor is None or not self.ready:
            # Compatibilidade de descritores legados: mantém a recuperação antiga.
            return True
        self.candidate_db = descriptor.power_db
        self.power_ratio = 10 ** ((descriptor.power_db - self.reference_db) / 10)
        self.high_return = bool(self.highs and descriptor.peak_high_db >= median(self.highs) - 6)
        novelty_return = self.spectral_novelty>=.22 and self.spectral_flux>=.10
        reinforced = self.high_return or self.pause_recent(event.occurred_at) or novelty_return or self.phase in ("impact","confirmed")
        self.score = (.35*min(1.0,self.power_ratio/1.25)+.25*max(self.spectral_flux,self.spectral_novelty)
                      +.20*max(0,min(1,event.confidence))+.20)
        threshold = self.FAST_POWER_RATIO if self.accelerated or not reinforced else self.MIN_POWER_RATIO
        if self.power_ratio < threshold:
            self.rejected_weak += 1
            self.weak_at = event.occurred_at
            self.reason = ("Kick acelerado do build" if self.accelerated else "Retorno de kick fraco") + f": {self.power_ratio:.0%} da potência de referência."
            return False
        self.reason = ("Média dos picos do groove atingida; " if self.mean_reached else "Retorno forte: ") + f"{self.power_ratio:.0%} da potência do groove."
        return True

    def recovered(self, descriptor, low, current_low, low_ref, break_low):
        # Um ataque real de força integral não espera a média da mixagem subir.
        # A identidade, a potência e o alinhamento são exigidos pelo chamador.
        if self.reaches_groove_mean(descriptor):
            return True
        # O pico do próprio ataque não espera a média de 600 ms recuperar.
        peak = descriptor.peak_low_db if descriptor is not None else -120
        returned = max(low, current_low, peak)
        # Um transiente separado do fundo, validado em timbre e potência,
        # também prova o retorno quando o baixo já sustentava a mixagem.
        return returned > low_ref - 4 and (returned - break_low >= 7
            or descriptor is not None and descriptor.early)

    def confirm(self,event,descriptor,at,period=.5):
        self.confirmation_ms = max(0.0,(at-event.occurred_at)*1000)
        self.fast_confirmed = bool(descriptor and descriptor.early)
        self.rescued_attack = bool(descriptor and descriptor.rescued)
        self.phase = "impact"
        self.continuation_count = 1
        self.continuation_deadline = at+max(1.25,3.5*period)

    def continue_drop(self,new_kicks,at,withdrawn=False):
        if self.phase!="impact":return True
        self.continuation_count += len(new_kicks)
        if self.continuation_count>=3:
            self.phase="confirmed"
        elif withdrawn:
            self.phase="rejected";self.rejected_impacts+=1
            self.reason="Impacto isolado: o retorno rítmico não continuou; retomando o contexto anterior."
            return False
        return True

    def snapshot(self, at, period, last_kick, armed):
        missing = max(0.0, (at - last_kick) / period) if last_kick is not None and period else 0.0
        if not armed and at - self.candidate_at < .8:
            missing = self.candidate_gap_beats
        pause = self.pause_recent(at)
        reason = self.reason if self.phase=="rejected" or at - self.candidate_at < .8 else (
            "Pausa antes do impacto; aguardando kick forte." if armed and pause else
            f"Retorno armado após {missing:.0f} tempos sem kick forte." if armed and missing >= 7.5 else "")
        return DropEvidenceSnapshot(self.reference_db, self.candidate_db,
            self.power_ratio, missing, armed, pause, self.accelerated,
            self.high_return, self.rejected_weak, reason,self.confirmation_ms,
            self.fast_confirmed,self.rescued_attack,self.spectral_flux,
            self.spectral_novelty,min(1.0,self.score),self.phase,self.rejected_impacts,
            reference_peak_db=self.reference_peak_db,peak_ratio=self.peak_ratio,
            reference_kicks=len(self.powers),mean_reached=self.mean_reached)
