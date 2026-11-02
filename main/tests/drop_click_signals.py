"""Casos conhecidos para replay; não substituem rótulos de música real."""
import numpy as np
from kick_masking_signals import drop_arrangement


def click_scene(*, level=.95, kind='kick', rate=48000, gain=.6, click='learned', offset=0):
    base = drop_arrangement(level,rate)
    x = np.concatenate((base[:12*rate],np.tile(base[12*rate:],(5,1))))
    t = np.arange(len(x))/rate
    if kind in ('bass_only','crash','pluck'):
        env = np.exp(-(t%.5)*24)*(t>=12)
        x[:,0] -= (.45*.7*env*np.sin(2*np.pi*70*t)).astype(np.float32)
        x[:,1] -= (.40*.7*env*np.sin(2*np.pi*85*t)).astype(np.float32)
        if kind=='pluck':
            env = np.exp(-(t%.5)*8)*(t>=12)
            x[:,0] += (.35*env*np.tanh(8*np.sin(2*np.pi*98*t))).astype(np.float32)
            x[:,1] += (.35*env*np.tanh(8*np.sin(2*np.pi*119*t))).astype(np.float32)
        if kind=='crash':
            age = np.maximum(t-12,0)
            x += (.15*(t>=12)*np.exp(-age/.08)*(np.sin(2*np.pi*2200*t)+np.sin(2*np.pi*5600*t)))[:,None].astype(np.float32)
    if kind=='weak_roll':
        env = np.exp(-(((t-9)*4)%1)*6)*((t>=9)&(t<12))
        x[:,0] += (.45*.7*.55*env*np.sin(2*np.pi*70*t)).astype(np.float32)
        x[:,1] += (.40*.7*.55*env*np.sin(2*np.pi*85*t)).astype(np.float32)
    if click!='none':
        delayed = np.where(t>=12,t-offset,t)
        pulse = .12*np.exp(-(delayed%.5)/.005)*(np.sin(2*np.pi*3100*delayed)+.5*np.sin(2*np.pi*4700*delayed))
        if click=='return_only':pulse *= t>=12
        x += pulse[:,None].astype(np.float32)
    return (x*gain).astype(np.float32)
