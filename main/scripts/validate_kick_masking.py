"""Matriz de mascaramento sintética; opcionalmente compara um wheel anterior."""
import argparse
import json
from pathlib import Path
import sys
from time import process_time,perf_counter
import numpy as np

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--reference-wheel',type=Path)
args=parser.parse_args()
if args.reference_wheel:sys.path.insert(0,str(args.reference_wheel.resolve()))
sys.path.insert(0,str(root/'tests'))
from beatlight import __version__
from beatlight.contracts import AudioBlock
from beatlight.dsp.pipeline import AudioAnalyzer
from kick_masking_signals import arrangement,drop_arrangement,event_metrics

def blocks(signal,rate=48000,chunk=512):
    for seq,first in enumerate(range(0,len(signal),chunk)):
        x=signal[first:first+chunk]
        if x.ndim==1:x=x[:,None]
        x=np.asarray(x,dtype=np.float32);x.setflags(write=False)
        yield AudioBlock('masked-qa',x,rate,x.shape[1],seq,len(x),first/rate,(first+len(x))/rate)

report={'version':__version__,'reference_only':bool(args.reference_wheel),'physical_audio_used':False,'synthetic_only':True,'tolerance_ms':75,'cases':{},'drops':{}}
cases=[(kind,kind,120) for kind in ('isolated','held','offbeat','rolling','compressed')]
cases.extend((f'offbeat_{bpm}','offbeat',bpm) for bpm in (100,128,150))
for key,kind,bpm in cases:
    signal,truth=arrangement(kind,bpm=bpm);analyzer=AudioAnalyzer();raw={};confirmed={};states=[];acquired=None
    start=perf_counter();cpu_start=process_time()
    for block in blocks(signal):
        snapshot=analyzer.process(block)
        assert not any((snapshot.kick_error,snapshot.beat_error,snapshot.structure_error,snapshot.kick_verification_error))
        if snapshot.kicks:
            for event in snapshot.kicks.events:raw[event.occurred_at]=event
        if snapshot.kick_verification:
            for event in snapshot.kick_verification.confirmed_events:confirmed[event.occurred_at]=event
        if snapshot.structure:
            if not states or states[-1]!=snapshot.structure.state:states.append(snapshot.structure.state)
            if acquired is None and snapshot.structure.grid.period:acquired=snapshot.structure.updated_at
    row={'raw':event_metrics(raw,truth),'confirmed':event_metrics(confirmed,truth),'states':states,'acquired_at':acquired,
      'cpu_seconds':round(process_time()-cpu_start,4),'wall_seconds':round(perf_counter()-start,4),'audio_seconds':len(signal)/48000,'signal_peak':float(abs(signal).max()),
      'spectral_candidates':sum(event.evidence=='spectral' for event in raw.values()) if hasattr(next(iter(raw.values()),None),'evidence') else 0,
      'bpm_target':bpm,'bpm':60/snapshot.structure.grid.period if snapshot.structure.grid.period else 0}
    report['cases'][key]=row;print(key,json.dumps(row),flush=True)
    if not args.reference_wheel and kind!='rolling':assert row['confirmed']['true']==len(truth) and row['confirmed']['false']==0,row
for level in (.30,.65):
    analyzer=AudioAnalyzer();first_drop=None;first_impact=None
    for block in blocks(drop_arrangement(level)):
        snapshot=analyzer.process(block)
        if snapshot.structure and snapshot.structure.state=='drop' and first_drop is None:
            first_drop=snapshot.structure.updated_at;first_impact=snapshot.structure.drop_at
    report['drops'][str(level)]={'first_decision':first_drop,'delay_ms':(first_drop-12)*1000 if first_drop else None}
    if not args.reference_wheel:assert first_drop is not None and 12<=first_drop<12.3,report['drops'][str(level)]
    print('drop',level,report['drops'][str(level)],flush=True)
report['passed']=True
path=root/'docs'/f'resultado-kick-masking-v{__version__}.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('APROVADO:',path,flush=True)
