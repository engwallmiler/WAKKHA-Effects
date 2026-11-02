"""Reaprendizado limitado por ataques observados, independente do perfil antigo."""
from collections import deque
from dataclasses import dataclass
import math
from statistics import median
from beatlight.music.peak_grid import cosine


@dataclass(frozen=True,slots=True)
class Observation:
    event: object
    descriptor: object
    envelope: tuple[float,...]


class RecurrentProfile:
    REQUIRED = 4

    def __init__(self):
        self.candidates = deque(maxlen=self.REQUIRED)
        self.offgrid = deque(maxlen=8)
        self.reason = 'Aguardando ataques reais na grade.'
        self.last_at = -math.inf
        self.relearns = 0

    def clear(self, reason):
        self.candidates.clear()
        self.reason = reason

    def expire(self, at, period):
        if self.candidates and (not period or at-self.last_at>period*1.6):
            self.clear('Sequência interrompida; aguardando novos ataques.')
        while self.offgrid and at-self.offgrid[0].event.occurred_at>max(1.,2*period):
            self.offgrid.popleft()

    def observe(self,event,descriptor,history,period,aligned):
        t = event.occurred_at
        if descriptor is None or not descriptor.transient_shape or not period:
            return False
        # Contraste e queda reais: não bastam relógio ou energia sustentada.
        rejection = ('Confiança acústica insuficiente.' if event.confidence<.65 else
            'Ataque abaixo do piso acústico.' if descriptor.peak_low_db<-60 else
            'Contraste do ataque insuficiente.' if descriptor.attack_db<3 else
            'Cauda sustentada; falta queda do ataque.' if descriptor.decay<1.5 else
            'Excesso de harmônicos no ataque.' if descriptor.harmonic_attack>.04 else '')
        if rejection:
            if aligned:self.clear(rejection)
            return False
        before = [10**(f.low_db/10) for f in history if t-.09<=f.at<=t-.025]
        base = median(before) if before else 0.
        samples = [max(0.,10**(min(history,key=lambda f:abs(f.at-t-age)).low_db/10)-base)
            for age in (-.02,0,.02,.04,.08,.12)]
        norm = max(samples)
        if not norm:return False
        observation = Observation(event,descriptor,tuple(v/norm for v in samples))
        if not aligned:
            self.offgrid.append(observation)
            return False
        for other in self.offgrid:
            gap = t-other.event.occurred_at
            if (abs(gap-period*.5)<=period*.14
                    and self.similar(observation,other,minimum_power=.25)):
                self.clear('Subdivisão semelhante entre os tempos; possível roll.')
                return False
        if self.candidates:
            gap = t-self.last_at
            if abs(gap-period)>period*.08 or not all(self.similar(observation,other) for other in self.candidates):
                self.clear('Novo desenho de ataque; reiniciando a comparação.')
        self.candidates.append(observation)
        self.last_at = t
        self.reason = f'Ataques reais compatíveis na grade: {len(self.candidates)}/{self.REQUIRED}.'
        return len(self.candidates)>=self.REQUIRED

    @staticmethod
    def similar(a,b,minimum_power=.45):
        da,db = a.descriptor,b.descriptor
        ratio = 10**((da.power_db-db.power_db)/10)
        return (cosine(da.transient_shape,db.transient_shape)>=.9
            and cosine(a.envelope,b.envelope)>=.88 and minimum_power<=ratio<=2.2
            and abs(da.decay-db.decay)<=max(4.,db.decay*.6))
