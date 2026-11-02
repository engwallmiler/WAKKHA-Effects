"""Reprodução causal de perfil antigo bloqueando kicks alinhados; sem hardware."""
import argparse,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--reference-wheel',type=Path)
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args()
if args.reference_wheel:sys.path.insert(0,str(args.reference_wheel.resolve()))
sys.path.insert(0,str(root/'tests'))
from beatlight import __version__
from beatlight.configuration.store import Settings
from beatlight.dsp.pipeline import AudioAnalyzer
from test_kicks import blocks
from kick_masking_signals import event_metrics
from recurrent_profile_signals import changed_kick_scene
report=dict(version=__version__,synthetic_only=True,physical_device_used=False,cases={})
for kind in ('kick','held','offbeat','harmonic','roll'):
    samples,truth=changed_kick_scene(kind=kind)
    a=AudioAnalyzer(beat_config=Settings().beat_config());events={};periods=set();available={}
    for block in blocks(samples):
        r=a.process(block)
        assert not r.structure_error and not r.kick_error
        if r.kick_verification:
            for event in r.kick_verification.confirmed_events:
                events[event.occurred_at]=event;available.setdefault(event.occurred_at,block.acquired_at+block.frames/block.sample_rate)
        if r.structure and r.structure.grid.tempo_locked:periods.add(r.structure.grid.period)
    row=dict(metrics=event_metrics(events,truth),after_change=sum(t>=5 for t in events),
        stable_bpms=sorted(60/p for p in periods),false_drops=r.structure.drop_id,
        final_state=r.structure.state,rejected_profile=r.structure.rejected_timbre,
        relearns=getattr(getattr(r.structure,'kick_recovery',None),'relearns',0))
    report['cases'][kind]=row;print(kind,json.dumps(row),flush=True)
    if not args.reference_wheel:
        assert periods=={60/127} and row['false_drops']==0,row
        if kind=='kick':
            assert row['metrics']['true']>=24 and row['metrics']['false']==0 and row['relearns']==1,row
        else:
            assert row['relearns']==0 and row['metrics']['false']<=(2 if kind=='roll' else 0),row
args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
