"""Confirmação estrutural independente: perfil grave e decaimento do kick aprendido."""
from collections import deque
from dataclasses import dataclass
import math
from statistics import median


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

    def push(self, feature, events, *, fast_return=False, after_pause=False, early_matches=None):
        self.history.append(feature)
        for event in sorted(events, key=lambda e: e.occurred_at):
            if not math.isfinite(event.occurred_at) or event.occurred_at > feature.at or event.confidence < 0.35:
                continue
            if event.occurred_at in self.pending:
                self.pending[event.occurred_at] = event
            elif event.occurred_at > self.cursor:
                self.cursor = event.occurred_at
                self.pending[event.occurred_at] = event
        result = []
        for t, event in tuple(self.pending.items()):
            early = fast_return and len(self.references) >= 4 and (early_matches is None or early_matches(event))
            wait = .09 if early else .12
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
        update = learn and (len(self.references)<4 or self.return_matches(event))
        descriptor = self.prepared.pop(event.occurred_at, None)
        if update and descriptor is not None:
            self.references.append(descriptor)

    def discard(self, event):
        self.prepared.pop(event.occurred_at, None)
