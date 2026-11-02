"""Troca de timbre sem mudar o BPM; ataques reais e negativos rotulados."""
import numpy as np


def changed_kick_scene(*,kind='kick',bpm=127,rate=48000,duration=14,gain=.4,frequency=45,restart_at=5):
    t=np.arange(round(rate*duration))/rate;period=60/bpm
    truth=np.arange(.8,duration-.3,period)
    signal=.025*np.sin(2*np.pi*440*t)
    for onset in truth:
        age=np.maximum(0,t-onset)
        if onset<5:
            envelope=np.where(t>=onset,(1-np.exp(-age/.0015))*np.exp(-age/.065),0)
            phase=2*np.pi*(52*age+65*.025*(1-np.exp(-age/.025)))
            signal+=.7*envelope*np.sin(phase)
        elif kind=='kick' and onset>=restart_at:
            # Corpo mais largo e timbre diferente, com um platô de ~60 ms.
            envelope=np.where(t>=onset,(1-np.exp(-age/.002))*np.exp(-np.maximum(0,age-.055)/.032),0)
            signal+=.65*envelope*np.sin(2*np.pi*frequency*age)
    if kind in ('kick','held'):
        signal+=.35*(1-np.exp(-np.maximum(0,t-5)/.08))*np.sin(2*np.pi*105*t)
    if kind in ('offbeat','harmonic','roll'):
        step=period/2 if kind=='roll' else period
        offset=period/2 if kind=='offbeat' else 0
        for onset in np.arange(truth[truth>=5][0]+offset,duration,step):
            age=np.maximum(0,t-onset)
            envelope=np.where(t>=onset,(1-np.exp(-age/.002))*np.exp(-age/.035),0)
            wave=np.sin(2*np.pi*72*age)
            if kind=='harmonic':wave=np.tanh(10*wave)
            signal+=(.3 if kind=='roll' else .65)*envelope*wave
    return np.asarray(signal*gain,dtype=np.float32),truth[(truth<5)|(truth>=restart_at)] if kind=='kick' else truth[truth<5]
