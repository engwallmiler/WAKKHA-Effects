"""Custo do DSP de produção, sem GUI/trace/hardware; comparação sequencial opcional."""
import argparse
import json
from pathlib import Path
import sys
from time import process_time
import numpy as np

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
from test_kicks import fixture_music,blocks

report={'version':__version__,'reference_only':bool(args.reference_wheel),'synthetic_only':True,
    'physical_device_used':False,'diagnostics_enabled':False,'cases':{}}
for kind in ('groove','groove_click'):
    samples,_=fixture_music(duration=8,gain=.7)
    if kind=='groove_click':
        t=np.arange(len(samples))/48000;phase=(t-.8)%(60/128)
        samples+=(.06*np.exp(-phase/.005)*np.sin(2*np.pi*3100*t)).astype(np.float32)
    runs=[]
    for repeat in range(3):
        analyzer=AudioAnalyzer(beat_config=Settings().beat_config());started=process_time()
        for block in blocks(samples):
            snapshot=analyzer.process(block)
            assert not snapshot.kick_error and not snapshot.structure_error
        runs.append(process_time()-started)
    report['cases'][kind]={'audio_seconds_per_run':8,'cpu_seconds':runs,
        'median_cpu_seconds':float(np.median(runs)), 'median_fraction_one_core':float(np.median(runs))/8,
        'kick_history':len(snapshot.kicks.history),'profile_history':len(analyzer._structure._identity.history),
        'click_history':len(analyzer._structure_features._click.history) if hasattr(analyzer._structure_features,'_click') else 0}
args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
