"""Compara drops rotulados sintéticos por replay PCM; opcionalmente usa wheel antigo."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import wave
import numpy as np

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--reference-wheel',type=Path)
args=parser.parse_args()
if args.reference_wheel:sys.path.insert(0,str(args.reference_wheel.resolve()))
sys.path.insert(0,str(root/'tests'))
from beatlight import __version__
from beatlight.configuration.store import Settings
from beatlight.dsp.pipeline import AudioAnalyzer
from drop_click_signals import click_scene

if args.reference_wheel:
    spec=importlib.util.spec_from_file_location('replay_reference_runner',root/'src/beatlight/diagnostics/replay.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    replay=module.replay
else:
    from beatlight.diagnostics.replay import replay

folder=root/'.runtime'/f'replay-validation-v{__version__}'
folder.mkdir(parents=True,exist_ok=True)
summary={'version':__version__,'reference_only':bool(args.reference_wheel),'synthetic_only':True,
    'physical_device_used':False,'causal':True,'cases':{}}
cases=[('normal',{'level':.3,'click':'none'}),('masked',{}),('very_masked',{'level':1.2}),
    ('weak_roll',{'kind':'weak_roll'}),('bass_only',{'kind':'bass_only'}),('crash',{'kind':'crash'}),
    ('pluck',{'kind':'pluck'}),('unlearned_click',{'click':'return_only'}),('late_click',{'offset':.09})]
for name,options in cases:
    x=click_scene(**options);assert abs(x).max()<1
    audio=folder/(name+'.wav');annotation=folder/(name+'.labels.json')
    with wave.open(str(audio),'wb') as output:
        output.setnchannels(2);output.setsampwidth(2);output.setframerate(48000)
        output.writeframes(np.rint(x*32767).astype('<i2').tobytes())
    negative=name in ('bass_only','crash','pluck')
    truth=[float(t) for t in np.arange(.5,6,.5)] + ([] if negative else [float(t) for t in np.arange(12,17,.5)])
    annotation.write_text(json.dumps({'version':1,'bpm':120,'regions':[[.5,17]],'kicks':truth,'drops':[] if negative else [12]}),encoding='utf-8')
    factory=(lambda diagnostic:AudioAnalyzer(beat_config=Settings().beat_config())) if args.reference_wheel else None
    report=replay(audio,annotation,trace_path=folder/(name+'.decisions.jsonl'),analyzer_factory=factory)
    report['synthetic_only']=True
    (folder/(name+'.report.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    metric=report['metrics']['drops'];row={key:metric[key] for key in ('true','false','missed','available_delay_ms')}
    row.update(kicks=report['metrics']['kicks'],decisions=report['decision_gates'],
        drop_positions=[drop['kick_counts'] for drop in report['detected_drops']],
        click_supported=any(drop['click_supported'] for drop in report['detected_drops']),
        performance=report['performance'])
    summary['cases'][name]=row
    print(name, {key:value for key,value in row.items() if key not in ('kicks','performance','decisions')},flush=True)
    if not args.reference_wheel:
        assert metric['false']==0,(name,metric)
        if name in ('normal','masked','very_masked','weak_roll'):
            assert metric['true']==1 and metric['available_delay_ms']['max']<150,(name,metric)
            assert report['detected_drops'][0]['kick_counts']==list(range(1,9)),(name,report['detected_drops'])
        if name in ('unlearned_click','late_click'):
            assert not row['click_supported'],name
summary['passed']=True
path=root/'docs'/f'resultado-replay-drop-v{__version__}.json'
path.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print('APROVADO:',path)
