"""Confirmação estrutural independente: perfil grave e decaimento do kick aprendido."""
from collections import deque
from dataclasses import dataclass, replace
import math
from statistics import median
from time import monotonic
from beatlight.contracts import KickEvent
from beatlight.music.peak_grid import cosine
from beatlight.music.recurrent_profile import RecurrentProfile


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
    grid_supported: bool = False
    click_attack: float = 0.0
    click_onset: bool = False
    click_shape: tuple[float, ...] = ()
    click_supported: bool = False
    peak_supported: bool = False
    recurrent_supported: bool = False


class KickIdentity:
    def __init__(self, diagnostics=None):
        self.diagnostics = diagnostics
        self.early_reason = ''
        self.history = deque(maxlen=64)
        self.pending = {}
        self.prepared = {}
        self.cursor = -math.inf
        self.references = deque(maxlen=16)
        self.reference_events = deque(maxlen=16)
        self.rejected = 0
        self.similarity = 0.0
        self.rejected_harmonics = 0
        self.rescued_at = -math.inf
        self.peak_pending = deque(maxlen=8)
        self.last_output = -math.inf
        self.recurrent = RecurrentProfile()
        self.last_reason = 'Aguardando candidatos.'

    def push(self, feature, events, *, fast_return=False, after_pause=False, early_matches=None, grid_matches=None,
             peak_matches=(), allow_peak_recovery=True, recurrent_period=0., recurrent_matches=None, recurrent_needed=False):
        self.history.append(feature)
        self.recurrent.expire(feature.at,recurrent_period)
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
                accepted = descriptor is not None and self._fast_matches(event, descriptor, after_pause)
                if self.diagnostics:
                    self.diagnostics({'kind':'identity','at':feature.at,'candidate_at':t,'stage':'early',
                        'gate':('identity_early_click_pass' if descriptor.attack_db<1.5 else 'identity_early_pass') if accepted else 'identity_early_'+(self.early_reason if descriptor else 'history'),
                        'accepted':accepted,'power_db':descriptor.power_db if descriptor else None,
                        'decay_db':descriptor.early_decay if descriptor else None,
                        'attack_db':descriptor.attack_db if descriptor else None,
                        'click_onset':descriptor.click_onset if descriptor else False})
                if accepted:
                    if descriptor.attack_db<1.5:
                        descriptor = replace(descriptor,click_supported=True)
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
            self.last_reason = 'Perfil inicial em aquisição.' if passed else 'Janela acústica incompleta.'
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
                        rescued=t==self.rescued_at,click_attack=measured.click_attack,
                        click_onset=measured.click_onset,click_shape=measured.click_shape)
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
                        shifted=self._shifted_similarity(shape,reference)
                        passed = ((similarity >= 0.72 or shifted>=.94) and not excess_harmonics
                            and (expected_decay < 3 or decay >= max(1.2, expected_decay * 0.3)))
                        self.last_reason = ('Espectro diferente do perfil.' if similarity<.72 and shifted<.94 else
                            'Harmônicos acima do perfil.' if excess_harmonics else
                            'Cauda diferente do perfil.' if not passed else 'Perfil aprovado.')
                        # Sob baixo contínuo, a cauda da MIXAGEM perde contraste.
                        # Uma grade inteira já estável permite usar a queda do
                        # transiente subtraído, sem abrir essa exceção a retornos
                        # de drop, candidatos fora da grade ou rolls fracos.
                        early_refs = [r.early_decay for r in self.references if r.early_decay is not None]
                        supported = bool(grid_matches and grid_matches(event) and event.confidence>=.7
                            and (similarity>=.8 or shifted>=.94) and not excess_harmonics
                            and descriptor.attack_db>=1.5 and descriptor.early_decay is not None
                            and early_refs and descriptor.early_decay>=max(.8,median(early_refs)*.3)
                            and descriptor.power_db>=median(r.power_db for r in self.references)+10*math.log10(.4))
                        if supported:
                            descriptor = replace(descriptor, grid_supported=True)
                            passed = True
                            self.last_reason = 'Grade e cauda curta confirmaram o ataque.'
                        if (not passed and measured is not None and grid_matches and grid_matches(event)
                                and event.confidence>=.7 and self._fast_matches(event,measured)
                                and self.early_reason=='click_pass'):
                            # Continuidade depois do oitavo kick: usa a MESMA
                            # evidência conservadora, aguardando a janela longa.
                            # Não reaprende o perfil com essa exceção.
                            descriptor = replace(descriptor,grid_supported=True,click_supported=True)
                            passed = True
            if recurrent_matches and descriptor is not None:
                if not passed or recurrent_needed:
                    recovered = self.recurrent.observe(event,descriptor,self.history,recurrent_period,recurrent_matches(event))
                    if recovered:
                        descriptor = replace(descriptor,grid_supported=True,recurrent_supported=True)
                        event = replace(event,evidence='grid-profile')
                        passed = True
                        self.last_reason = 'Recorrência validada; novo perfil pronto.'
                elif recurrent_matches(event):
                    self.recurrent.clear('Perfil atual confirmando os ataques.')
            if self.diagnostics:
                self.diagnostics({'kind':'identity','at':feature.at,'candidate_at':t,'stage':'full',
                    'gate':'identity_recurrent_pass' if descriptor and descriptor.recurrent_supported else 'identity_full_pass' if passed else 'identity_full_reject','accepted':bool(passed),
                    'similarity':self.similarity,'power_db':descriptor.power_db if descriptor else None,
                    'decay_db':descriptor.decay if descriptor else None,
                    'harmonic_attack':descriptor.harmonic_attack if descriptor else None,'reason':self.last_reason})
            if passed:
                self.prepared[t] = descriptor
                result.append(event)
            else:
                self.rejected += 1
        if allow_peak_recovery:
            self.peak_pending.extend(peak_matches)
        else:
            self.peak_pending.clear()
        # Primeiro deixar a confirmação normal terminar. A recuperação não
        # substitui ataques bons nem muda o aprendizado já estabelecido.
        while self.peak_pending and feature.at-self.peak_pending[0].event.occurred_at>=.14:
            match = self.peak_pending.popleft()
            event = match.event
            last_output = max(self.last_output,max((e.occurred_at for e in result),default=-math.inf))
            if event.occurred_at-last_output<.18:
                continue
            descriptor = self._describe(event.occurred_at)
            if descriptor is None or not self._peak_matches(match, descriptor):
                continue
            self.rescued_at = event.occurred_at
            self.cursor = max(self.cursor,event.occurred_at)
            self.prepared[event.occurred_at] = replace(descriptor,grid_supported=True,peak_supported=True)
            result.append(event)
            if self.diagnostics:
                self.diagnostics({'kind':'identity','at':feature.at,'candidate_at':event.occurred_at,
                    'stage':'peak','gate':'identity_peak_grid_pass','accepted':True,
                    'similarity':match.spectral,'envelope_similarity':match.envelope,
                    'power_ratio':match.power_ratio,'phase_error_ms':match.error_ms})
        return tuple(sorted(result, key=lambda e: e.occurred_at))

    def commit_recurrent(self):
        """Troca atômica após a estrutura validar fase e espaçamento."""
        if len(self.recurrent.candidates)<self.recurrent.REQUIRED:
            return ()
        items = tuple((o.event,replace(o.descriptor,recurrent_supported=False)) for o in self.recurrent.candidates)
        self.references.clear();self.references.extend(d for _,d in items)
        self.reference_events.clear();self.reference_events.extend(items)
        self.peak_pending.clear()
        self.recurrent.relearns += 1
        self.recurrent.clear('Perfil reaprendido por quatro ataques reais na grade.')
        return tuple(self.references)

    def _peak_matches(self, match, descriptor):
        """Recuperação no groove: recorrência e perfil aprendido independentes.

        O máximo real tem uma fase diferente do início do ataque. Não serve
        para reaprender o BPM, o perfil ou para antecipar um drop.
        """
        refs = [r for r in self.references if r.early_decay is not None
            and len(r.transient_shape)==len(descriptor.transient_shape)]
        if len(refs)<4 or match.spectral<.9 or match.envelope<.82 or match.power_ratio<.55:
            return False
        reference = tuple(sum(r.transient_shape[i] for r in refs)/len(refs)
            for i in range(len(descriptor.transient_shape)))
        return (cosine(descriptor.transient_shape,reference)>=.9
            and descriptor.early_decay>=max(.8,median(r.early_decay for r in refs)*.3)
            and descriptor.harmonic_attack<=max(.04,median(r.harmonic_attack for r in refs)*4+.025))

    def peak_seed_matches(self, peak):
        """Seleciona a fase por assinatura do kick, e não pela grade antiga."""
        refs = [r for r in self.references if len(r.transient_shape)==len(peak.shape)]
        if len(refs)<4:
            return False
        shape = tuple(sum(r.transient_shape[i] for r in refs)/len(refs) for i in range(len(peak.shape)))
        power = median(10**(r.power_db/10) for r in refs)
        return cosine(peak.shape,shape)>=.9 and .45<=peak.power/max(1e-12,power)<=4

    def _rescue_attack(self, feature, matches):
        """Candidato acústico contextual quando o detector geral perde o ataque.

        A grade só limita a janela de procura. Sem aumento real de potência não
        há evento; identidade, decaimento e energia ainda precisam aprová-lo.
        """
        if len(self.references)<4 or not feature.low_shape:
            return
        if feature.at-self.cursor<.18:
            # Um roll fora da grade pode consumir o refratário do detector geral
            # imediatamente antes do impacto. Ele não bloqueia um NOVO ataque
            # alinhado; candidatos alinhados/recentemente recuperados continuam
            # protegidos contra duplicação.
            previous=KickEvent(self.cursor,self.cursor,0,.75)
            if (feature.at-self.cursor<.06 or feature.at-self.rescued_at<.18
                    or matches is None or matches(previous)):
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
        # A cauda abaixo do fundo é incerta, não uma queda de mais de 100 dB.
        # Piso relativo preserva a invariância ao ganho e evita aprender um
        # decaimento impossível quando a bassline mascara a cauda do kick.
        tail_floor=max(1e-12,attack*.001,base*.02)
        tail_attack = max(tail_floor,average(tail,"low_db")-base)
        # Retira o leito que já tocava, inclusive da assinatura espectral.
        compatible = [f for f in before if len(f.low_shape)==len(peak.low_shape)]
        spectral = [max(0.0, value*value*power(peak.bass_db if peak.bass_db>-120 else peak.low_db)
            - sum(f.low_shape[i]**2*power(f.bass_db if f.bass_db>-120 else f.low_db)
                  for f in compatible)/len(compatible) if compatible else value*value)
            for i,value in enumerate(peak.low_shape)]
        norm = math.sqrt(max(1e-12,sum(spectral)))
        shape = tuple(math.sqrt(v)/norm for v in spectral)
        decay = max(0.0,10*math.log10(attack/tail_attack))
        # Centro da FFT do clique pode preceder o corpo filtrado por ~30 ms.
        # Esta janela é só de coincidência; não altera timestamps nem a grade.
        click_frames = [f for f in self.history if t-.045<=f.at<=t+.025]
        clicked = [f for f in click_frames if f.click_onset and f.click_shape]
        click_peak = max(click_frames,key=lambda f:f.click_db) if click_frames else peak
        click_before = [f for f in self.history if t-.12<=f.at<=t-.055]
        click_attack = max(0.0,power(click_peak.click_db)-average(click_before,'click_db'))/attack
        return Fingerprint(peak.low_shape,decay,
            max(0.0,power(peak.harmonic_db)-average(before,"harmonic_db"))/attack,
            max(0.0,peak.low_db-10*math.log10(max(base,1e-12))),
            10*math.log10(attack),peak.low_db,max(f.high_db for f in around),peak.harmonic_db,
            decay,shape,max(0.0,max(power(f.high_db) for f in around)-average(before,"high_db"))/attack,
            early,t==self.rescued_at,click_attack=click_attack,
            click_onset=bool(clicked),click_shape=click_peak.click_shape)

    def _fast_matches(self, event, descriptor, after_pause=False):
        refs = [r for r in self.references if r.early_decay is not None
                and len(r.transient_shape)==len(descriptor.transient_shape)]
        if len(refs)<4 or event.confidence<.45:
            self.early_reason = 'references_or_confidence'
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
        spectral=cosine>=.9 or self._shifted_similarity(shape,reference)>=.94
        # Exceção estreita ao contraste da MIXAGEM: clique aprendido coincidente
        # + transiente grave de potência integral + MESMA forma/queda/harmônicos.
        # Não aprende referência, não altera grade e não aceita click/hats sós.
        click_support = False
        click_reason = 'attack'
        if spectral and decay_ok and harmonics<=limit and .35<=descriptor.attack_db<1.5:
            clicked = [r for r in refs if r.click_onset and r.click_attack>.001 and len(r.click_shape)==len(descriptor.click_shape)]
            if len(clicked)>=4 and descriptor.click_onset and descriptor.click_shape:
                click_reference = tuple(sum(r.click_shape[i] for r in clicked)/len(clicked) for i in range(len(descriptor.click_shape)))
                similarity = sum(a*b for a,b in zip(descriptor.click_shape,click_reference))/max(1e-12,
                    math.sqrt(sum(a*a for a in descriptor.click_shape)*sum(b*b for b in click_reference)))
                ratio = descriptor.click_attack/max(1e-12,median(r.click_attack for r in clicked))
                click_support = bool(similarity>=.9 and .25<=ratio<=4
                    and descriptor.power_db>=median(r.power_db for r in refs)+10*math.log10(1.25))
                if similarity>=.9 and .25<=ratio<=4 and not click_support:
                    click_reason = 'click_body_power'
        self.early_reason = ('shape' if not spectral else 'decay' if not decay_ok else
            'harmonics' if harmonics>limit else click_reason if descriptor.attack_db<1.5 and not click_support else 'click_pass' if click_support else 'pass')
        return spectral and decay_ok and harmonics<=limit and (descriptor.attack_db>=1.5 or click_support)

    @staticmethod
    def _shifted_similarity(shape,reference):
        """Tolerância estreita de altura: no máximo um bin do FFT estrutural.

        A queda e os harmônicos continuam obrigatórios. Não se usa esta
        tolerância para corrigir a fase da grade.
        """
        if len(shape)<6 or len(shape)!=len(reference):return 0.0
        norm=sum(v*v for v in shape)
        best=0.0
        for shift in (-1,1):
            shifted=tuple(reference[i-shift] if 0<=i-shift<len(reference) else 0.0 for i in range(len(reference)))
            if sum(v*v for v in shifted)<.9*sum(v*v for v in reference):continue
            score=sum(a*b for a,b in zip(shape,shifted))/max(1e-12,math.sqrt(norm*sum(v*v for v in shifted)))
            best=max(best,score)
        return best

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
        if descriptor.early or descriptor.peak_supported or descriptor.recurrent_supported:
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
        if descriptor is not None and (descriptor.peak_supported or descriptor.recurrent_supported):
            return False
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
        spectral=cosine>=.9 or self._shifted_similarity(descriptor.shape,reference)>=.94
        return (spectral and minimum_decay<=descriptor.decay<=max(16,decay*1.8)
                and self._harmonic_excess(descriptor, refs, after_pause)<=harmonic_limit
                and descriptor.attack_db>=attack_limit)

    def accept(self, event, learn):
        self.last_output = max(self.last_output,event.occurred_at)
        descriptor = self.prepared.get(event.occurred_at)
        update = learn and not (descriptor and (descriptor.early or descriptor.peak_supported or descriptor.recurrent_supported)) and (len(self.references)<4 or self.return_matches(event))
        descriptor = self.prepared.pop(event.occurred_at, None)
        if update and descriptor is not None:
            self.references.append(descriptor)
            self.reference_events.append((event,descriptor))

    def align_references(self,predicate):
        """Na primeira aquisição, não aprender os baixos fora da grade escolhida."""
        if len(self.reference_events)==len(self.references):
            aligned=[item for item in self.reference_events if predicate(item[0])]
            self.reference_events.clear();self.reference_events.extend(aligned)
            self.references.clear();self.references.extend(descriptor for _,descriptor in aligned)
        return tuple(self.references)

    def discard(self, event):
        self.prepared.pop(event.occurred_at, None)
