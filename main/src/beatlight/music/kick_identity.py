"""Confirmação estrutural independente: perfil grave e decaimento do kick aprendido."""
from collections import deque
from dataclasses import dataclass, replace
import math
from statistics import median
from time import monotonic
from beatlight.contracts import KickEvent


@dataclass(frozen=True, slots=True)
class Fingerprint:
    shape: tuple[float, ...]
    decay: float
    harmonic_attack: float
    attack_db: float = 0.0
    power_db: float = -120.0
    peak_low_db: float = -120.0
    peak_high_db: float = -120.0
    peak_harmonic_db: float = -120.0
    early_decay: float | None = None
    transient_shape: tuple[float, ...] = ()
    high_attack: float = 0.0
    early: bool = False
    rescued: bool = False


class KickIdentity:
    def __init__(self):
        self.history = deque(maxlen=64)
        self.pending = {}
        self.prepared = {}
        self.cursor = -math.inf
        self.references = deque(maxlen=16)
        self.rejected = 0
        self.similarity = 0.0
        self.rejected_harmonics = 0
        self.rescued_at = -math.inf

    def push(self, feature, events, *, fast_return=False, after_pause=False, early_matches=None):
        self.history.append(feature)
        for event in sorted(events, key=lambda e: e.occurred_at):
            if not math.isfinite(event.occurred_at) or event.occurred_at > feature.at or event.confidence < 0.35:
                continue
            if abs(event.occurred_at-self.rescued_at)<.12:
                continue  # o detector principal pode publicar o mesmo ataque depois
            if event.occurred_at in self.pending:
                self.pending[event.occurred_at] = event
            elif event.occurred_at > self.cursor:
                self.cursor = event.occurred_at
                self.pending[event.occurred_at] = event
        if fast_return:
            self._rescue_attack(feature, early_matches)
        result = []
        for t, event in tuple(self.pending.items()):
            early = fast_return and len(self.references) >= 4 and (early_matches is None or early_matches(event))
            # O retorno tem uma decisão própria: não espera os 120 ms usados
            # para aprender o perfil e corrigir a grade. Uma tentativa incerta
            # permanece pendente para a análise completa do MESMO ataque.
            if early and feature.low_shape and feature.at-t >= .055:
                descriptor = self._describe(t, early=True)
                if descriptor is not None and self._fast_matches(event, descriptor, after_pause):
                    del self.pending[t]
                    self.prepared[t] = descriptor
                    result.append(event)
                    continue
            wait = .12
            if feature.low_shape and feature.at - t < wait:
                continue
            del self.pending[t]
            around = [f for f in self.history if t - 0.025 <= f.at <= t + 0.045 and f.low_shape]
            tail = [f.low_db for f in self.history if t + 0.08 <= f.at <= t + 0.13]
            descriptor = None
            passed = not feature.low_shape or bool(around and tail)
            if around and tail:
                peak = max(around, key=lambda f: f.low_db)
                before = [f for f in self.history if t - 0.09 <= f.at <= t - 0.025]
                base_low = sum(10 ** (f.low_db / 10) for f in before) / len(before) if before else 0.0
                base_harmonic = sum(10 ** (f.harmonic_db / 10) for f in before) / len(before) if before else 0.0
                low_attack = max(1e-12, 10 ** (peak.low_db / 10) - base_low)
                harmonic_attack = max(0.0, 10 ** (peak.harmonic_db / 10) - base_harmonic) / low_attack
                descriptor = Fingerprint(peak.low_shape, max(0.0, peak.low_db - sum(tail) / len(tail)),
                    harmonic_attack, max(0.0, peak.low_db-10*math.log10(max(base_low,1e-12))),
                    10 * math.log10(low_attack), peak.low_db,
                    max(f.high_db for f in around), peak.harmonic_db)
                measured = self._describe(t)
                if measured is not None:
                    descriptor = replace(descriptor, early_decay=measured.early_decay,
                        transient_shape=measured.transient_shape, high_attack=measured.high_attack,
                        rescued=t==self.rescued_at)
                if len(self.references) >= 4:
                    shape, decay = descriptor.shape, descriptor.decay
                    width = len(shape)
                    compatible = [r.shape for r in self.references if len(r.shape) == width]
                    if compatible:
                        reference = tuple(sum(s[i] for s in compatible) / len(compatible) for i in range(width))
                        similarity = sum(a * b for a, b in zip(shape, reference)) / max(1e-12,
                            math.sqrt(sum(a * a for a in shape) * sum(b * b for b in reference)))
                        self.similarity = similarity
                        expected_decay = median(r.decay for r in self.references)
                        harmonic_limit = max(0.04, median(r.harmonic_attack for r in self.references) * 4 + 0.025)
                        excess_harmonics = self._harmonic_excess(descriptor, self.references, after_pause) > harmonic_limit
                        if excess_harmonics:
                            self.rejected_harmonics += 1
                        passed = (similarity >= 0.72 and not excess_harmonics
                            and (expected_decay < 3 or decay >= max(1.2, expected_decay * 0.3)))
            if passed:
                self.prepared[t] = descriptor
                result.append(event)
            else:
                self.rejected += 1
        return tuple(sorted(result, key=lambda e: e.occurred_at))

    def _rescue_attack(self, feature, matches):
        """Candidato acústico contextual quando o detector geral perde o ataque.

        A grade só limita a janela de procura. Sem aumento real de potência não
        há evento; identidade, decaimento e energia ainda precisam aprová-lo.
        """
        if len(self.references)<4 or not feature.low_shape or feature.at-self.cursor<.18:
            return
        before = [f for f in self.history if .03 <= feature.at-f.at <= .10]
        if len(before)<2:
            return
        base = median(10**(f.low_db/10) for f in before)
        current = 10**(feature.low_db/10)
        reference = median(10**(r.power_db/10) for r in self.references)
        if feature.low_db < -60 or current < base*2 or current-base < reference*.3:
            return
        candidate = KickEvent(feature.at,monotonic(),.8,.75)
        if matches is not None and not matches(candidate):
            return
        self.rescued_at = self.cursor = feature.at
        self.pending[feature.at] = candidate

    def _describe(self, t, *, early=False):
        around = [f for f in self.history if t-.025 <= f.at <= t+.035 and f.low_shape]
        tail = [f for f in self.history if t+.035 <= f.at <= t+.055]
        if not around or not tail:
            return None
        peak = max(around, key=lambda f:f.low_db)
        before = [f for f in self.history if t-.09 <= f.at <= t-.025]
        power = lambda db: 10**(db/10)
        average = lambda frames, field: sum(power(getattr(f,field)) for f in frames)/len(frames) if frames else 0.0
        base = average(before,"low_db")
        attack = max(1e-12,power(peak.low_db)-base)
        tail_attack = max(1e-12,average(tail,"low_db")-base)
        # Retira o leito que já tocava, inclusive da assinatura espectral.
        compatible = [f for f in before if len(f.low_shape)==len(peak.low_shape)]
        spectral = [max(0.0, value*value*power(peak.bass_db if peak.bass_db>-120 else peak.low_db)
            - sum(f.low_shape[i]**2*power(f.bass_db if f.bass_db>-120 else f.low_db)
                  for f in compatible)/len(compatible) if compatible else value*value)
            for i,value in enumerate(peak.low_shape)]
        norm = math.sqrt(max(1e-12,sum(spectral)))
        shape = tuple(math.sqrt(v)/norm for v in spectral)
        decay = max(0.0,10*math.log10(attack/tail_attack))
        return Fingerprint(peak.low_shape,decay,
            max(0.0,power(peak.harmonic_db)-average(before,"harmonic_db"))/attack,
            max(0.0,peak.low_db-10*math.log10(max(base,1e-12))),
            10*math.log10(attack),peak.low_db,max(f.high_db for f in around),peak.harmonic_db,
            decay,shape,max(0.0,max(power(f.high_db) for f in around)-average(before,"high_db"))/attack,
            early,t==self.rescued_at)

    def _fast_matches(self, event, descriptor, after_pause=False):
        refs = [r for r in self.references if r.early_decay is not None
                and len(r.transient_shape)==len(descriptor.transient_shape)]
        if len(refs)<4 or event.confidence<.45:
            return False
        reference = tuple(sum(r.transient_shape[i] for r in refs)/len(refs)
                          for i in range(len(descriptor.transient_shape)))
        shape = descriptor.transient_shape
        cosine = sum(a*b for a,b in zip(shape,reference))/max(1e-12,
            math.sqrt(sum(a*a for a in shape)*sum(b*b for b in reference)))
        expected = median(r.early_decay for r in refs)
        # Cauda curta comparada com a MESMA janela do groove. A análise longa
        # continua obrigatória para alterar o perfil ou a fase da grade.
        decay_ok = descriptor.early_decay >= max(.8,expected*.55)
        harmonics = self._harmonic_excess(descriptor,refs,after_pause)
        # Pratos/crashes simultâneos não são harmônicos do baixo. O desconto
        # requer um ataque agudo muito acima do groove e é limitado pela sua potência.
        if descriptor.peak_high_db >= median(r.peak_high_db for r in refs)+8:
            harmonics = max(0.0,harmonics-min(.5,descriptor.high_attack))
        limit = max(.025,median(r.harmonic_attack for r in refs)*3+.015)
        self.similarity = cosine
        # Um kick sobre baixo contínuo pode acrescentar só 1,5–4 dB à mixagem.
        # A potência absoluta do transiente é validada depois, contra o groove.
        return cosine>=.9 and decay_ok and harmonics<=limit and descriptor.attack_db>=1.5

    def descriptor(self, event):
        return self.prepared.get(event.occurred_at)

    def correction_matches(self, event):
        """Mudar a grade exige identidade mais próxima que confirmar um ataque.

        Basslines percussivas podem passar pela triagem normal; um desvio de fase
        não deve relaxar essa triagem justamente durante o breakdown.
        """
        descriptor = self.prepared.get(event.occurred_at)
        if descriptor is None:
            return not self.references  # descritores legados sem perfil; não usados pelo extrator real
        if descriptor.early:
            return False
        if len(self.references) < 4:
            return False
        compatible = [r for r in self.references if len(r.shape) == len(descriptor.shape)]
        if not compatible:
            return False
        reference = tuple(sum(r.shape[i] for r in compatible) / len(compatible) for i in range(len(descriptor.shape)))
        cosine = sum(a * b for a, b in zip(descriptor.shape, reference)) / max(1e-12,
            math.sqrt(sum(a * a for a in descriptor.shape) * sum(b * b for b in reference)))
        decay = median(r.decay for r in compatible)
        decay_matches = 0.85 * decay <= descriptor.decay <= 1.3 * decay if decay >= 3 else abs(descriptor.decay - decay) <= 2
        harmonic_limit = max(0.02, median(r.harmonic_attack for r in compatible) * 3 + 0.015)
        return cosine >= 0.9 and decay_matches and descriptor.harmonic_attack <= harmonic_limit

    @staticmethod
    def _harmonic_excess(descriptor, refs, after_pause):
        excess = descriptor.harmonic_attack
        if after_pause and len(refs) >= 4:
            # Ao retornar do silêncio, a melodia aprendida também reaparece.
            # Desconta só esse leito anterior, com teto de 6% da potência do kick.
            bed = median(10 ** (r.peak_harmonic_db / 10) for r in refs)
            allowance = min(.06, bed / max(1e-12, 10 ** (descriptor.power_db / 10)))
            excess = max(0.0, excess - allowance)
        return excess

    def return_matches(self, event, *, after_pause=False):
        """Entrar no drop exige um transiente próximo do kick aprendido."""
        descriptor = self.prepared.get(event.occurred_at)
        if descriptor is None:
            return not self.references  # compatibilidade de descritores legados
        if descriptor.early:
            return self._fast_matches(event,descriptor,after_pause)
        if len(self.references)<4 or event.confidence<.55:
            return False
        refs = [r for r in self.references if len(r.shape)==len(descriptor.shape)]
        if len(refs)<4:
            return False
        reference = tuple(sum(r.shape[i] for r in refs)/len(refs) for i in range(len(descriptor.shape)))
        cosine = sum(a*b for a,b in zip(descriptor.shape,reference))/max(1e-12,
            math.sqrt(sum(a*a for a in descriptor.shape)*sum(b*b for b in reference)))
        decay = median(r.decay for r in refs)
        minimum_decay = max(1.5,decay*.65) if decay>=3 else max(.6,decay*.5)
        harmonic_limit = max(.02,median(r.harmonic_attack for r in refs)*3+.015)
        attack_limit = max(1.5,min(4.5,median(r.attack_db for r in refs)*.3))
        return (cosine>=.9 and minimum_decay<=descriptor.decay<=max(16,decay*1.8)
                and self._harmonic_excess(descriptor, refs, after_pause)<=harmonic_limit
                and descriptor.attack_db>=attack_limit)

    def accept(self, event, learn):
        descriptor = self.prepared.get(event.occurred_at)
        update = learn and not (descriptor and descriptor.early) and (len(self.references)<4 or self.return_matches(event))
        descriptor = self.prepared.pop(event.occurred_at, None)
        if update and descriptor is not None:
            self.references.append(descriptor)

    def discard(self, event):
        self.prepared.pop(event.occurred_at, None)
