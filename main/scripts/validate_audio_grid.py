"""Grade estimada só pelo áudio, com ataques de baixo 110 ms antes do kick."""
import argparse
import json
from pathlib import Path
import sys
from time import process_time

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--reference-wheel', type=Path)
parser.add_argument('--output', type=Path)
args = parser.parse_args()
if args.reference_wheel:
    sys.path.insert(0, str(args.reference_wheel.resolve()))
sys.path.insert(0, str(root/'tests'))
from beatlight import __version__
from beatlight.configuration.store import Settings
from beatlight.dsp.pipeline import AudioAnalyzer
from test_stable_audio_grid import early_bass_arrangement
from test_kicks import blocks
from kick_masking_signals import event_metrics

report = {'version':__version__, 'reference_only':bool(args.reference_wheel),
    'synthetic_only':True, 'physical_device_used':False, 'external_clock_used':False,
    'tolerance_ms':75, 'bass_lead_ms':110, 'cases':{}}
for bpm in (100, 128, 150):
    samples, truth = early_bass_arrangement(bpm=bpm)
    analyzer = AudioAnalyzer(beat_config=Settings().beat_config())
    raw = {}; confirmed = {}; periods = set(); guided = False; locked_at = None
    started = process_time()
    for block in blocks(samples):
        snapshot = analyzer.process(block)
        assert not any((snapshot.kick_error, snapshot.beat_error, snapshot.structure_error, snapshot.kick_verification_error))
        if snapshot.kicks:
            raw.update((e.occurred_at, e) for e in snapshot.kicks.events)
            guided |= getattr(snapshot.kicks, 'grid_guided', False)
        if snapshot.kick_verification:
            confirmed.update((e.occurred_at, e) for e in snapshot.kick_verification.confirmed_events)
        if snapshot.structure and snapshot.structure.grid.period and getattr(snapshot.structure.grid, 'tempo_locked', False):
            periods.add(snapshot.structure.grid.period)
            if locked_at is None:
                locked_at = snapshot.structure.updated_at
    row = {'raw':event_metrics(raw, truth), 'confirmed':event_metrics(confirmed, truth),
        'bpm_target':bpm, 'final_bpm':60/snapshot.structure.grid.period if snapshot.structure.grid.period else None,
        'stable_bpms':sorted(60/p for p in periods), 'locked_at':locked_at, 'guided':guided,
        'offgrid_attacks':getattr(snapshot.kicks, 'offgrid_count', None),
        'cpu_seconds':round(process_time()-started,4), 'audio_seconds':len(samples)/48000}
    report['cases'][str(bpm)] = row
    print(bpm, json.dumps(row), flush=True)
    if not args.reference_wheel:
        assert row['confirmed']['true'] == len(truth) and row['confirmed']['false'] == 0, row
        assert guided and periods == {60/bpm} and row['offgrid_attacks'] > 0, row
report['passed'] = True
output = args.output or root/'docs'/f'resultado-grade-audio-v{__version__}.json'
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('APROVADO:', output)
