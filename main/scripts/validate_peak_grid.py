"""Replay por blocos conhecidos; compara picos recuperados sem usar hardware."""
import argparse
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--reference-wheel',type=Path)
parser.add_argument('--out',type=Path,required=True)
args = parser.parse_args()
if args.reference_wheel:
    sys.path.insert(0,str(args.reference_wheel.resolve()))
sys.path.insert(0,str(root/'tests'))
from beatlight import __version__
from beatlight.configuration.store import Settings
from beatlight.dsp.pipeline import AudioAnalyzer
from peak_grid_signals import masked_groove
from test_kicks import blocks
from kick_masking_signals import event_metrics

cases = [
    ('bass65',dict(bass=.95),48000,512),
    ('bass65_strong',dict(bass=1.2),48000,512),
    ('bass105',dict(bass=.95,frequency=105),48000,512),
    ('bass105_44100',dict(bass=.95,frequency=105),44100,113),
    ('held_without_kicks',dict(bass=.95,remove_kicks=True),48000,512),
    ('offbeat_without_kicks',dict(bass=.95,remove_kicks=True,offbeat=True),48000,512),
]
report = dict(version=__version__,synthetic_only=True,physical_device_used=False,
    external_clock_used=False,reference_only=bool(args.reference_wheel),tolerance_ms=75,cases={})
for name,kwargs,rate,chunk in cases:
    samples,truth = masked_groove(rate=rate,**kwargs)
    analyzer = AudioAnalyzer(beat_config=Settings().beat_config())
    confirmed = {}; recovered = {}; periods = set(); available = {}
    for block in blocks(samples,rate=rate,chunk=chunk):
        result = analyzer.process(block)
        assert not any((result.kick_error,result.beat_error,result.structure_error,result.kick_verification_error))
        if result.kick_verification:
            for event in result.kick_verification.confirmed_events:
                confirmed[event.occurred_at] = event
                available.setdefault(event.occurred_at,block.acquired_at+block.frames/rate)
                if event.evidence=='grid-peak':recovered[event.occurred_at] = event
        if result.structure and result.structure.grid.tempo_locked:
            periods.add(result.structure.grid.period)
    row = dict(confirmed=event_metrics(confirmed,truth),recovered=event_metrics(recovered,truth),
        recovered_count=len(recovered),stable_bpms=sorted(60/p for p in periods),
        false_drops=result.structure.drop_id,
        max_recovery_availability_ms=round(max((available[t]-min(truth,key=lambda x:abs(x-t)) for t in recovered),default=0)*1000,2))
    report['cases'][name] = row
    print(name,json.dumps(row),flush=True)
    if not args.reference_wheel:
        assert row['confirmed']['false']==0 and not row['false_drops']
        assert periods=={60/128}
args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
