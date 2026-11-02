"""Picos acústicos recorrentes sobre um período conhecido, sem estimar outro BPM.

Usa somente os descritores do FFT estrutural existente. O relógio abre janelas;
espectro, envoltória e potência precisam provar um novo ataque dentro delas.
"""
from collections import deque
from dataclasses import dataclass
import math
from statistics import median
from time import monotonic
import numpy as np
from beatlight.contracts import KickEvent, PeakGridSnapshot


def cosine(a,b):
    if len(a)!=len(b) or not a:
        return 0.
    return sum(x*y for x,y in zip(a,b))/max(1e-15,math.sqrt(sum(x*x for x in a)*sum(y*y for y in b)))


@dataclass(frozen=True,slots=True)
class Peak:
    at: float
    power: float
    shape: tuple[float,...]
    envelope: tuple[float,...]
    harmonics: float


@dataclass(frozen=True,slots=True)
class PeakMatch:
    event: KickEvent
    spectral: float
    envelope: float
    power_ratio: float
    error_ms: float


class PeakGridTracker:
    def __init__(self,floor_db=-60,diagnostics=None):
        self.diagnostics=diagnostics
        self.floor=10**(floor_db/10)
        self.frames=deque(maxlen=64)
        self.background=deque(maxlen=32)
        self.floor_bins=None
        self.pending=deque(maxlen=8)
        self.seeds=deque(maxlen=16)
        self.references=deque(maxlen=8)
        self.events=deque(maxlen=16)
        self.history=deque(maxlen=200)
        self.slots={}
        self.period=0.;self.anchor=None;self.stable_since=None;self.at=None
        self.last_index=0;self.last_match=None;self.last_peak=-math.inf
        self.count=self.rejected_grid=self.rejected_shape=0
        self.spectral=self.envelope=self.ratio=self.error_ms=0.

    @property
    def ready(self):
        return self.anchor is not None and len(self.references)>=3

    def reset_tempo(self,period,at):
        self.period=period;self.anchor=None;self.stable_since=at
        self.pending.clear();self.seeds.clear();self.references.clear();self.slots.clear()
        self.last_index=0;self.last_match=None

    def process(self,feature,period=0.,*,phase_hint=None,stable=False,learn=True,seed_matches=None):
        at=feature.at
        if not feature.low_shape or period<=0 or not math.isfinite(period):
            return ()
        if not self.period or abs(period/self.period-1)>.006:
            self.reset_tempo(period,at)
        self.at=at
        # Um período já estabilizado pela grade dispensa uma segunda espera.
        trusted=stable or at-self.stable_since>=max(.8,2*period)
        bins=np.square(feature.low_shape)*10**(feature.bass_db/10)
        if self.floor_bins is None or len(bins)!=len(self.floor_bins):
            self.floor_bins=bins.copy();self.background.clear();self.frames.clear()
        if len(self.background)>=12 and feature.frame_id%5==0:
            values=np.asarray(self.background)
            self.floor_bins=np.partition(values,len(values)//4,axis=0)[len(values)//4]
        residual=np.maximum(bins-self.floor_bins,0)
        power=float(residual.sum());total=max(float(bins.sum()),1e-15)
        shape=tuple(float(v) for v in np.sqrt(residual/max(power,1e-15)))
        harmonic=10**(feature.harmonic_db/10)/max(power,1e-15)
        self.frames.append((at,power,shape,harmonic,total))
        self.background.append(bins)
        self.history.append((at,power))
        if trusted and len(self.frames)>=5:
            older,peak,current=list(self.frames)[-3:]
            before=min(item[1] for item in list(self.frames)[-5:-2])
            if (peak[1]>older[1] and peak[1]>=current[1] and peak[1]>=self.floor
                    and peak[1]/peak[4]>=.045 and peak[1]-before>=peak[4]*.025
                    and peak[0]-self.last_peak>=.055):
                self.pending.append(peak);self.last_peak=peak[0]
        while self.pending and at-self.pending[0][0]>=.026:
            peak=self.pending.popleft();t,power,shape,harmonic,_=peak
            samples=[min(self.frames,key=lambda row:abs(row[0]-(t+age)))[1] for age in (-.03,-.02,-.01,0,.01,.02)]
            norm=max(samples)
            if not norm or min(samples[:2])>power*.8 or min(samples[-2:])>power*.97:
                continue
            observation=Peak(t,power,shape,tuple(v/norm for v in samples),harmonic)
            # Um perfil aprendido permite buscar a fase independentemente da
            # grade anterior; ela própria pode estar deslocada. Sem esse perfil,
            # a indicação de fase continua protegendo a aquisição inicial.
            if phase_hint is not None and seed_matches is None:
                error=abs((t-phase_hint+period/2)%period-period/2)
                if error>period*.18:
                    self.rejected_grid+=1;continue
            if not self.ready:
                if learn and (seed_matches is None or seed_matches(observation)):
                    self._acquire(observation)
            if self.ready:
                index=round((t-self.anchor)/self.period)
                if index<=self.last_index:
                    continue
                error=t-(self.anchor+index*self.period)
                if abs(error)>self.period*.12:
                    self.rejected_grid+=1;continue
                bucket=self.slots.setdefault(index,[])
                if len(bucket)<4:bucket.append(observation)
        result=[]
        if self.ready:
            for index in sorted(tuple(self.slots)):
                target=self.anchor+index*self.period
                if at<target+self.period*.12:
                    continue
                choices=self.slots.pop(index)
                if index<=self.last_index:
                    continue
                reference=self.references[-1]
                options=[]
                for peak in choices:
                    spectral=cosine(peak.shape,reference.shape);envelope=cosine(peak.envelope,reference.envelope)
                    ratio=peak.power/median(r.power for r in self.references)
                    if self.diagnostics:
                        self.diagnostics({'kind':'peak_grid','at':at,'candidate_at':peak.at,
                            'spectral':spectral,'envelope':envelope,'ratio':ratio,
                            'harmonics':peak.harmonics,'harmonic_limit':max(.08,median(r.harmonics for r in self.references)*3+.02)})
                    if spectral>=.90 and envelope>=.82 and .4<=ratio<=4 and peak.harmonics<=max(.08,median(r.harmonics for r in self.references)*3+.02):
                        options.append((spectral*.5+envelope*.3+min(1,ratio)*.2,peak,spectral,envelope,ratio))
                if not options:
                    self.rejected_shape+=1;continue
                _,peak,self.spectral,self.envelope,self.ratio=max(options,key=lambda item:item[0])
                self.error_ms=(peak.at-target)*1000
                self.last_index=index;self.last_match=peak.at;self.count+=1
                event=KickEvent(peak.at,monotonic(),min(1,math.sqrt(self.ratio)),.9,'grid-peak')
                result.append(PeakMatch(event,self.spectral,self.envelope,self.ratio,self.error_ms));self.events.append(event)
                # Fase corrige ruído aos poucos. O período informado não é ajustado.
                self.anchor+=max(-self.period*.025,min(self.period*.025,peak.at-target))*.2
                if learn and .6<=self.ratio<=1.6 and self.envelope>=.9:
                    self.references.append(peak)
        return tuple(result)

    def _acquire(self,peak):
        candidates=[]
        for earlier,chain in self.seeds:
            if (abs(peak.at-earlier.at-self.period)<=self.period*.08
                    and cosine(peak.shape,earlier.shape)>=.92 and cosine(peak.envelope,earlier.envelope)>=.90
                    and .5<=peak.power/earlier.power<=2 and peak.harmonics<=max(.08,earlier.harmonics*3+.02)):
                candidates.append(chain+[peak])
        chain=max(candidates,key=lambda rows:(len(rows),sum(p.power for p in rows))) if candidates else [peak]
        self.seeds.append((peak,chain[-3:]))
        if len(chain)>=3:
            self.references.extend(chain[-3:]);self.anchor=peak.at-self.period*2
            self.last_index=1

    def snapshot(self,at):
        ready=self.ready
        next_at=self.anchor+(math.floor((at-self.anchor)/self.period)+1)*self.period if ready else None
        state='tracking' if ready and self.last_match is not None and at-self.last_match<1.7*self.period else 'predicting' if ready else 'learning'
        references=len(self.references) if ready else max((len(chain) for _,chain in self.seeds),default=0)
        return PeakGridSnapshot(at,state,self.period,self.anchor,self.count,references,self.last_match,next_at,
            self.spectral,self.envelope,self.ratio,self.error_ms,self.rejected_grid,self.rejected_shape,
            tuple(self.events),tuple(self.history))
