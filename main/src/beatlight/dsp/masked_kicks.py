"""Novidade causal por banda: o baixo tonal não normaliza todo o ataque.

Reutiliza o FFT do detector. Branqueamento local e máximo espectral no passado
reduzem a influência de componentes sustentados e de pequenas mudanças de nota.
Este módulo propõe candidatos; não reconhece um instrumento nem prevê kicks.
"""
from collections import deque
from math import exp,sqrt
from statistics import median
import numpy as np


class MaskedKickOnset:
    def __init__(self,frequencies,config):
        self.config=config
        step=frequencies[1]-frequencies[0]
        self.select=(frequencies>=config.kick_low_hz)&(frequencies<max(300,config.kick_high_hz+100)+step)
        freq=frequencies[self.select];split=sqrt(config.kick_low_hz*config.kick_high_hz)
        # Um bin de ~23 Hz já é um salto grande no subgrave. Não espalhar o
        # baixo de 105 Hz sobre um kick de 70 Hz ao suprimir vibrato.
        self.spread=freq>=max(200,8*step)
        self.body=freq<=config.kick_high_hz
        self.bands=[(freq<split),(freq>=split)&self.body,
                    (freq>config.kick_high_hz)&(freq<max(300,config.kick_high_hz+100))]
        self.background=None;self.previous=deque(maxlen=2);self.scores=deque(maxlen=100)
        self.history=deque(maxlen=200);self.threshold=.16;self.score=0.;self.excess=0.;self.rising=False
        self.pending_reference=None;self.pending_bins=None;self.sustained=0.
        self.count=0;self._frame=0

    def process(self,power,at):
        current=power[self.select]
        self._frame+=1;score=0.;self.excess=0.
        self.sustained=0.
        if self.pending_reference is not None:
            bins=self.pending_bins
            self.sustained=float(np.maximum(current[bins]-self.pending_reference[bins],0).sum()/max(float(current[self.body].sum()),1e-12))
        reference=difference=None
        if self.background is not None and len(self.previous)==2:
            previous=self.previous[0]
            # Mesmo denominador nos dois frames: adaptação do fundo não cria ataques.
            floor=np.maximum(self.background,max(float(self.background[self.body].max())*.002,1e-12))
            reference=previous.copy()
            reference[1:]=np.maximum(reference[1:],previous[:-1])
            reference[:-1]=np.maximum(reference[:-1],previous[1:])
            reference=np.where(self.spread,reference,previous)
            difference=np.maximum(0,np.log1p(current/floor)-np.log1p(reference/floor))
            values=[float(difference[mask].mean()) if mask.any() else 0. for mask in self.bands]
            novelty=.55*values[0]+.45*values[1]+.15*min(values[2],1.)
            score=1-exp(-novelty)
            self.excess=float(np.maximum(current[self.body]-previous[self.body],0).sum()/max(float(current[self.body].sum()),1e-12))
        if self._frame%5==0 and self.scores:
            center=median(self.scores);mad=median(abs(value-center) for value in self.scores)
            self.threshold=min(.8,max(.16,center+3*mad+.055)/self.config.kick_sensitivity)
        self.rising=score>self.score*1.025 and score-self.score>.015
        self.score=score;self.scores.append(score);self.history.append((at,score,self.threshold))
        self.background=current.copy() if self.background is None else self.background+.012*(current-self.background)
        self.previous.append(current)
        proposed=bool(self._frame>=25 and self.rising and score>=self.threshold and self.excess>=.035)
        self.pending_reference=reference if proposed else None
        self.pending_bins=(difference>.08)&self.body if proposed else None
        return proposed
