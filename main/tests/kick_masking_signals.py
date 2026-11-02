"""Arranjos determinísticos para medir mascaramento; não representam faixas reais."""
import numpy as np


def arrangement(kind,rate=48000,duration=7,bpm=120,gain=.7,kicks=True):
    t=np.arange(round(rate*duration))/rate;period=60/bpm
    truth=np.arange(.8,duration-.3,period)
    kick=np.zeros_like(t);bass=np.zeros_like(t)
    for onset in truth:
        a=np.maximum(t-onset,0);env=np.where(t>=onset,(1-np.exp(-a/.0015))*np.exp(-a/.065),0)
        phase=2*np.pi*(52*a+65*.025*(1-np.exp(-a/.025)))
        kick+=.7*env*np.sin(phase)
    if kind=='held':bass=.65*np.sin(2*np.pi*65*t)
    elif kind!='isolated':
        step=period/4 if kind=='rolling' else period
        notes=np.arange(.8+period/2,duration,step)
        for i,onset in enumerate(notes):
            a=np.maximum(t-onset,0);freq=[49,65.4,73.4,55][i%4]
            env=np.where((t>=onset)&(a<step+.15),(1-np.exp(-a/.014))*np.exp(-a/(.22 if kind=='rolling' else .30)),0)
            phase=2*np.pi*freq*a
            wave=np.sin(phase)+.23*np.sin(2*phase)+.12*np.sin(3*phase)
            bass+=(.65 if kind=='rolling' else .95)*env*wave
    hats=.025*np.sin(2*np.pi*7000*t)*np.exp(-(np.mod(t-.8,period/2))/.022)
    signal=(kick if kicks else 0)+bass+hats
    if kind=='compressed':signal=np.tanh(signal*2)/2
    return np.asarray(signal*gain,dtype=np.float32),truth if kicks else np.array([])


def event_metrics(times,truth,tolerance=.075):
    remaining=list(truth);errors=[];false=0
    for time in sorted(times):
        nearest=min(remaining,key=lambda t:abs(time-t)) if remaining else None
        if nearest is not None and abs(time-nearest)<=tolerance:
            remaining.remove(nearest);errors.append(time-nearest)
        else:false+=1
    return {'true':len(errors),'missed':len(remaining),'false':false,'truth':len(truth),
        'max_error_ms':round(max(map(abs,errors),default=0)*1000,2)}


def drop_arrangement(bass_level=.65,rate=48000):
    t=np.arange(rate*13)/rate;phase=t%.5;level=(t<6)|(t>=12)
    left=.45*np.exp(-phase*24)*level*np.sin(2*np.pi*70*t)
    right=.40*np.exp(-phase*24)*level*np.sin(2*np.pi*85*t)
    melody=.05*(np.sin(2*np.pi*440*t)+np.sin(2*np.pi*660*t))
    roll=(t>=9)&(t<12);roll_phase=(t-9)*4+(t-9)**2
    snare=.12*roll*np.exp(-(roll_phase%1)*18)*np.sin(2*np.pi*1100*t)
    hats=.025*np.exp(-((t*4)%1)*15)*np.sin(2*np.pi*6500*t)
    bass=bass_level*(t>=6)*np.sin(2*np.pi*105*t)
    return np.asarray(np.column_stack((left+melody+snare+hats+bass,right+melody+snare+hats+bass))*.7,dtype=np.float32)
