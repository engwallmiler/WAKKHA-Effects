"""Replay PCM em blocos, sem relógio externo, captura, Qt ou saídas físicas.

Rótulos entram apenas na avaliação. A latência usa o último sample entregue ao
analisador, nunca o centro de uma FFT nem o relógio real de uma execução rápida.
"""
from bisect import bisect_left, bisect_right
from collections import deque
from dataclasses import asdict
import json
import math
from pathlib import Path
from time import perf_counter, process_time
import wave
import numpy as np
from beatlight import __version__
from beatlight.configuration.store import Settings
from beatlight.contracts import AudioBlock
from beatlight.dsp.pipeline import AudioAnalyzer


STATES = {'warming', 'groove', 'breakdown', 'buildup', 'drop', 'silence'}


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Os tempos e valores devem ser números finitos.')
    return float(value)


def labels_for(path, duration):
    path = Path(path)
    if path.stat().st_size>16000000:
        raise ValueError('Arquivo de rótulos excede 16 MB.')
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or type(data.get('version')) is not int or data['version'] != 1:
        raise ValueError('Use um arquivo de rótulos com version: 1.')
    bpm = number(data.get('bpm', 128))
    if not 40 <= bpm <= 240:
        raise ValueError('BPM dos rótulos deve estar entre 40 e 240.')
    regions = data.get('regions', [[0, duration]])
    if not isinstance(regions, list) or not regions or len(regions)>2000:
        raise ValueError('regions deve conter intervalos completos de avaliação.')
    checked = []
    for region in regions:
        if not isinstance(region, list) or len(region) != 2:
            raise ValueError('Cada região deve ser [início, fim], em segundos.')
        start, end = map(number, region)
        if not 0 <= start < end <= duration + 1e-6:
            raise ValueError('Região de avaliação fora do áudio.')
        checked.append([start, min(duration, end)])
    checked.sort()
    if any(a[1] > b[0] for a, b in zip(checked, checked[1:])):
        raise ValueError('Regiões de avaliação não podem se sobrepor.')
    result = {'version':1, 'bpm':bpm, 'regions':checked}
    for kind in ('kicks', 'drops'):
        if kind not in data:
            continue  # ausente não equivale a uma região negativa
        if not isinstance(data[kind], list) or len(data[kind]) > 200000:
            raise ValueError(f'{kind} deve ser uma lista com até 200.000 tempos.')
        times = sorted(number(t) for t in data[kind])
        if any(not 0 <= t < duration for t in times) or any(b-a < 1e-6 for a,b in zip(times,times[1:])):
            raise ValueError(f'Tempos inválidos ou duplicados em {kind}.')
        result[kind] = times
    segments = []
    states = data.get('states', [])
    if not isinstance(states,list) or len(states)>200000:
        raise ValueError('states deve ser uma lista de segmentos.')
    for item in states:
        if not isinstance(item,dict):
            raise ValueError('Cada segmento deve ter start, end e state.')
        start, end = number(item.get('start')), number(item.get('end'))
        if item.get('state') not in STATES or not 0 <= start < end <= duration + 1e-6:
            raise ValueError('Segmento de estrutura inválido.')
        segments.append({'start':start, 'end':min(end,duration), 'state':item['state']})
    segments.sort(key=lambda item:item['start'])
    if any(a['end'] > b['start'] for a,b in zip(segments,segments[1:])):
        raise ValueError('Segmentos de estrutura não podem se sobrepor.')
    result['states'] = segments
    return result


def in_regions(at, regions):
    return any(start <= at < end for start,end in regions)


def event_metrics(truth, detections, regions, tolerance):
    """Associação única por menor distância, sem recontar um mesmo evento."""
    truth = [t for t in truth if in_regions(t,regions)]
    # Um ataque estimado alguns ms antes da borda ainda pode corresponder a um
    # rótulo dentro dela. Candidatos externos só entram como possíveis matches.
    detections = [d for d in detections if in_regions(d['at'],regions) or
        bisect_left(truth,d['at']-tolerance)<bisect_right(truth,d['at']+tolerance)]
    pairs = []
    for i,detection in enumerate(detections):
        for j in range(bisect_left(truth,detection['at']-tolerance), bisect_right(truth,detection['at']+tolerance)):
            pairs.append((abs(detection['at']-truth[j]), j, i))
    used_truth, used_events, matches = set(), set(), []
    for _, j, i in sorted(pairs):
        if j in used_truth or i in used_events:
            continue
        used_truth.add(j); used_events.add(i)
        matches.append({'truth_at':truth[j], **detections[i],
            'timestamp_error_ms':(detections[i]['at']-truth[j])*1000,
            'available_delay_ms':(detections[i]['available_at']-truth[j])*1000})
    delays = [item['available_delay_ms'] for item in matches]
    minutes = sum(end-start for start,end in regions)/60
    false_events = [d for i,d in enumerate(detections) if i not in used_events and in_regions(d['at'],regions)]
    tp, fp, fn = len(matches), len(false_events), len(truth)-len(matches)
    return {'truth':len(truth), 'true':tp, 'false':fp, 'missed':fn,
        'precision':tp/(tp+fp) if tp+fp else None, 'recall':tp/(tp+fn) if tp+fn else None,
        'false_per_minute':fp/minutes if minutes else None, 'tolerance_ms':tolerance*1000,
        'available_delay_ms':{'median':float(np.median(delays)), 'p95':float(np.percentile(delays,95)),
            'max':max(delays), 'within_150ms':sum(0<=d<=150 for d in delays),
            'early':sum(d<0 for d in delays)} if delays else None,
        'matches':sorted(matches,key=lambda item:item['truth_at']),
        'missed_at':[t for j,t in enumerate(truth) if j not in used_truth],
        'false_events':false_events}


def structure_metrics(segments, transitions, regions, duration):
    confusion = {}; correct = total = 0.
    spans = [(item['available_at'], transitions[i+1]['available_at'] if i+1<len(transitions) else duration, item['state'])
        for i,item in enumerate(transitions)]
    for segment in segments:
        for lo,hi in regions:
            for start,end,state in spans:
                overlap = max(0,min(segment['end'],hi,end)-max(segment['start'],lo,start))
                if overlap:
                    row = confusion.setdefault(segment['state'],{})
                    row[state] = row.get(state,0)+overlap
                    total += overlap
                    if state==segment['state']:
                        correct += overlap
    return {'evaluated_seconds':total, 'accuracy_by_time':correct/total if total else None,
        'confusion_seconds':confusion}


def decode_pcm(raw, width, channels):
    if width == 1:
        samples = (np.frombuffer(raw,dtype=np.uint8).astype(np.float32)-128)/128
    elif width == 3:
        parts = np.frombuffer(raw,dtype=np.uint8).reshape(-1,3).astype(np.int32)
        signed = parts[:,0] | (parts[:,1]<<8) | (parts[:,2]<<16)
        samples = ((signed ^ 0x800000)-0x800000).astype(np.float32)/8388608
    else:
        samples = np.frombuffer(raw,dtype='<i2' if width==2 else '<i4').astype(np.float32)/(2**(width*8-1))
    samples = samples.reshape(-1,channels)
    samples.setflags(write=False)
    return samples


def replay(audio, labels, *, block_size=512, settings=None, trace_path=None, analyzer_factory=None, progress=None):
    if type(block_size) is not int or not 64 <= block_size <= 8192:
        raise ValueError('Tamanho de bloco deve estar entre 64 e 8192 samples.')
    settings = settings or Settings()
    audio = Path(audio)
    try:
        stream = wave.open(str(audio),'rb')
    except (wave.Error, EOFError) as exc:
        raise ValueError('Use áudio WAV PCM de 8/16/24/32 bits, sem compressão.') from exc
    with stream:
        rate, channels, width, frames = stream.getframerate(),stream.getnchannels(),stream.getsampwidth(),stream.getnframes()
        if stream.getcomptype() != 'NONE' or not 8000<=rate<=192000 or not 1<=channels<=8 or width not in (1,2,3,4) or frames<=0:
            raise ValueError('Formato WAV PCM não suportado ou arquivo vazio.')
        duration = frames/rate
        annotation = labels_for(labels,duration)
        raw_events, kicks, drops, transitions = {}, {}, {}, []
        gate_counts = {}; processing = deque(maxlen=8192); processing_max = 0.; available = 0.; last_progress = -1
        trace = Path(trace_path).open('w',encoding='utf-8') if trace_path else None
        def decision(item):
            gate = item.get('gate',item['kind'])
            gate_counts[gate] = gate_counts.get(gate,0)+1
            if trace:
                trace.write(json.dumps({**item,'available_at':available},ensure_ascii=False,allow_nan=False)+'\n')
        started, cpu = perf_counter(), process_time()
        first = sequence = 0
        try:
            analyzer = analyzer_factory(decision) if analyzer_factory else AudioAnalyzer(
                settings.silence_db, settings.dsp_config(), settings.kick_config(),settings.beat_config(), diagnostics=decision)
            while first < frames:
                raw = stream.readframes(min(block_size,frames-first))
                expected = min(block_size,frames-first)*channels*width
                if len(raw) != expected:
                    raise ValueError('WAV truncado: o áudio termina antes do tamanho declarado.')
                samples = decode_pcm(raw,width,channels)
                available = (first+len(samples))/rate
                result = analyzer.process(AudioBlock('causal-replay', samples,rate,channels,sequence,len(samples),first/rate,available))
                errors = [getattr(result,key) for key in ('analysis_error','kick_error','beat_error','structure_error','texture_error','kick_verification_error') if getattr(result,key)]
                if errors:
                    raise RuntimeError('Falha do analisador: '+'; '.join(errors))
                processing.append(result.processing_ms)
                processing_max = max(processing_max,result.processing_ms)
                if result.kicks:
                    for event in result.kicks.events:
                        raw_events.setdefault(event.occurred_at,{'at':event.occurred_at,'available_at':available,'sensor':event.evidence})
                if result.kick_verification:
                    for event in result.kick_verification.confirmed_events:
                        kicks.setdefault(event.occurred_at,{'at':event.occurred_at,'available_at':available,'sensor':event.evidence})
                if result.structure:
                    s = result.structure
                    if not transitions or transitions[-1]['state']!=s.state:
                        transitions.append({'state':s.state,'at':s.updated_at,'available_at':available,'reason':s.reason})
                    if s.state=='drop':
                        drop = drops.setdefault(s.drop_id,{'at':s.drop_at,'available_at':available,'id':s.drop_id,
                            'kick_counts':[],'click_supported':bool(s.drop_evidence and getattr(s.drop_evidence,'click_supported',False))})
                        if s.drop_kicks not in drop['kick_counts']:
                            drop['kick_counts'].append(s.drop_kicks)
                        if s.drop_evidence and s.drop_evidence.phase=='confirmed':
                            drop.setdefault('continuity_confirmed_at',available)
                first += len(samples); sequence += 1
                if progress and int(available)>=last_progress+5:
                    progress(available,duration); last_progress=int(available)
        finally:
            if trace:
                trace.close()
        cpu_seconds, wall = process_time()-cpu, perf_counter()-started
    report = {'version':__version__,'audio':str(audio.resolve()),'labels':str(Path(labels).resolve()),
        'synthetic_only':False, 'causal':True,'physical_output':False,'external_clock':False,
        'sample_rate':rate,'channels':channels,'sample_width':width,'audio_seconds':duration,'blocks':sequence,
        'block_size':block_size,'grid_mode':settings.beat_grid_mode,
        'fixed_bpm':settings.beat_fixed_bpm if settings.beat_grid_mode=='manual' else None,
        'analysis_parameters':{'dsp':asdict(settings.dsp_config()),'kick':asdict(settings.kick_config()),'beat':asdict(settings.beat_config())},
        'label_bpm_used_only_for_scoring':annotation['bpm'], 'regions':annotation['regions'],
        'performance':{'cpu_seconds':cpu_seconds,'wall_seconds':wall,'cpu_fraction_of_one_core':cpu_seconds/duration,
            'processing_ms_p50':float(np.median(processing)),'processing_ms_p95':float(np.percentile(processing,95)),
            'processing_percentiles_window':'last_8192_blocks',
            'processing_ms_max':processing_max,'block_budget_ms':block_size/rate*1000},
        'raw_candidates':list(raw_events.values()),'confirmed_kicks':list(kicks.values()),
        'detected_drops':list(drops.values()),'transitions':transitions,'decision_gates':gate_counts,
        'annotations':annotation, 'metrics':{}}
    for kind,events,tolerance in [('kicks',kicks.values(),.075),('drops',drops.values(),60/annotation['bpm'])]:
        report['metrics'][kind] = event_metrics(annotation[kind],list(events),annotation['regions'],tolerance) if kind in annotation else None
    report['metrics']['structure'] = structure_metrics(annotation['states'],transitions,annotation['regions'],duration)
    return report
