"""Rastreio sintético do retorno, sem hardware nem conexão de rede."""
from dataclasses import asdict
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tests"))
import numpy as np
from test_drop_energy_pipeline import composition
from beatlight.contracts import AudioBlock
from beatlight.dsp.pipeline import AudioAnalyzer

analyzer = AudioAnalyzer()
gate = analyzer._structure._identity
original = gate.push

def trace(feature, events, **kwargs):
    found = original(feature, events, **kwargs)
    for event in found:
        if 119.8 <= event.occurred_at <= 120.6:
            d = gate.descriptor(event)
            print("CANDIDATE", feature.at, event.occurred_at, "strict",gate.return_matches(event),
                "reference", analyzer._structure._drop_detector.reference_db,
                "pause", analyzer._structure._drop_detector.pause_recent(feature.at),
                "fingerprint",asdict(d) if d else None,
                "ref",asdict(gate.references[-1]) if gate.references else None)
    return found

for seq,first in enumerate(range(0,48000*21,512)):
    t = np.arange(first,first+512)/48000
    x = composition(t)
    x.setflags(write=False)
    at = 100+first/48000
    snapshot=analyzer.process(AudioBlock("trace",x,48000,2,seq,512,at,at+512/48000))
    if seq==0:
        gate=analyzer._structure._identity
        original=gate.push
        gate.push=trace
    if snapshot.structure and 119.9 < snapshot.structure.updated_at < 120.7:
        s = snapshot.structure
        if seq%4==0:
            print("STATE",s.updated_at,s.state,s.reason)
