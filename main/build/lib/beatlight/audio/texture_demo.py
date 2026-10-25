"""Ciclo de 24 s: groove, bassline sem kick, textura densa e retorno. Sem reprodução."""
import numpy as np


def texture_demo_samples(t):
    position=np.asarray(t)%24
    groove=(position<6)|(position>=18)
    kick=np.exp(-((position*2)%1)*12)*groove
    riff=(position>=6)&(position<18)
    phase=(position-0.25)%0.5
    notes=np.array((65.0,82.0,98.0,73.0))
    note=notes[(np.floor((position-0.25)*2).astype(int)%4)]
    bass=0.32*np.exp(-phase*10)*np.tanh(10*np.sin(2*np.pi*note*phase))*riff
    dense=position>=12
    layers=sum(0.045*np.sin(2*np.pi*f*t) for f in (330,700,1500,3200,6500,12000))*dense
    hats=0.05*np.exp(-((position*8)%1)*16)*np.sin(2*np.pi*9000*t)*dense
    left=0.45*kick*np.sin(2*np.pi*70*t)+bass+layers+hats+0.02*np.sin(2*np.pi*440*t)
    right=0.4*kick*np.sin(2*np.pi*85*t)+bass+layers+hats+0.02*np.sin(2*np.pi*660*t)
    return np.column_stack((left,right)).astype(np.float32)
