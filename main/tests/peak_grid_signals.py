"""Sinais determinísticos, sem clique agudo, para a grade de picos."""
import numpy as np


def masked_groove(*, bass=.65, frequency=65, bpm=128, rate=48000, duration=12,
                  gain=.45, remove_kicks=False, offbeat=False):
    t = np.arange(round(rate*duration))/rate
    period = 60/bpm
    truth = np.arange(.8, duration-.3, period)
    signal = .01*np.sin(2*np.pi*440*t)
    signal += bass*(1-np.exp(-np.maximum(t-5,0)/.08))*np.sin(2*np.pi*frequency*t)
    for onset in truth:
        if remove_kicks and onset>=5:
            continue
        age = np.maximum(t-onset,0)
        envelope = np.where(t>=onset,(1-np.exp(-age/.0015))*np.exp(-age/.065),0)
        phase = 2*np.pi*(52*age+65*.025*(1-np.exp(-age/.025)))
        signal += .7*envelope*np.sin(phase)
    if offbeat:
        for onset in truth[truth>=5]+period/2:
            age = np.maximum(t-onset,0)
            envelope = np.where(t>=onset,(1-np.exp(-age/.002))*np.exp(-age/.035),0)
            signal += .7*envelope*np.sin(2*np.pi*110*age)
    return np.asarray(signal*gain,dtype=np.float32), truth[truth<5] if remove_kicks else truth
