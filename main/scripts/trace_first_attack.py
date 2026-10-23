"""Diagnóstico offline dos perfis de retorno; nenhuma fonte real é aberta."""
from dataclasses import asdict
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tests"))
import numpy as np
from test_drop_first_attack import track
from beatlight.contracts import AudioBlock
from beatlight.dsp.pipeline import AudioAnalyzer

variation = {"bass":True} if len(sys.argv)<2 else {sys.argv[1]:float(sys.argv[2]) if len(sys.argv)>2 else True}
pluck = "pluck" in variation
if "dense" in variation:
    variation={"bass":True,"bass_level":.30,"bass_from":6}
if pluck:
    variation={}
analyzer=AudioAnalyzer()
for seq,first in enumerate(range(0,48000*13,512)):
    t=np.arange(first,first+512)/48000
    x=track(t,**variation)
    if pluck:
        from beatlight.audio.demo import structure_demo_samples
        if first<48000*6:
            x=structure_demo_samples(t)
        else:
            env=np.exp(-(t%.5)*8)*(t>=9)
            x=np.column_stack((.02*np.sin(2*np.pi*440*t)+.45*env*np.sin(2*np.pi*70*t),
                .02*np.sin(2*np.pi*660*t)+.40*env*np.sin(2*np.pi*85*t))).astype(np.float32)
    x.setflags(write=False)
    at=100+first/48000
    if seq == 1:
        gate=analyzer._structure._identity
        original=gate.push
        original_fast=gate._fast_matches
        traced=set()
        def trace_fast(event,descriptor,after_pause=False):
            passed=original_fast(event,descriptor,after_pause)
            if 111.9<event.occurred_at<112.1 and event.occurred_at not in traced:
                traced.add(event.occurred_at)
                print("FAST",passed,"similarity",gate.similarity,"fingerprint",asdict(descriptor),
                    "ref",asdict(gate.references[-1]))
            return passed
        gate._fast_matches=trace_fast
        def trace(feature,events,**kw):
            found=original(feature,events,**kw)
            for event in found:
                if (108.9 if pluck else 111.9)<event.occurred_at<(112 if pluck else 112.7):
                    d=gate.descriptor(event)
                    print("CANDIDATE",feature.at,event,gate.return_matches(event),
                        "descriptor",asdict(d) if d else None,"ref",asdict(gate.references[-1]))
            return found
        gate.push=trace
    s=analyzer.process(AudioBlock("trace",x,48000,2,seq,512,at,at+512/48000))
    if 111.9<at<112.7 and seq%5==0:
        print("STATE",at,s.structure.state,s.structure.reason,"raw",s.kicks.last_event,"break_low",analyzer._structure._break_low)
print("REJECTIONS",s.structure.rejected_timbre,s.structure.rejected_returns)
