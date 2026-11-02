import json
import wave
from pathlib import Path
import numpy as np
import pytest
from beatlight.diagnostics.replay import decode_pcm,event_metrics,labels_for,replay
from beatlight.replay import main,preview
from beatlight.configuration.store import Settings
from dataclasses import asdict
from kick_masking_signals import arrangement


def wav(path,samples,rate=48000):
    if samples.ndim==1:
        samples=samples[:,None]
    with wave.open(str(path),'wb') as output:
        output.setnchannels(samples.shape[1]);output.setsampwidth(2);output.setframerate(rate)
        output.writeframes(np.rint(np.clip(samples,-1,1)*32767).astype('<i2').tobytes())


def labels(path,**changes):
    path.write_text(json.dumps({'version':1,**changes}),encoding='utf-8')
    return path


def test_pcm_decoding_keeps_signed_24bit_and_unsigned_8bit_center():
    assert decode_pcm(bytes([0,128,255]),1,1).ravel()==pytest.approx([-1,0,127/128])
    assert decode_pcm(bytes([0,0,128,0,0,0,255,255,127]),3,1).ravel()==pytest.approx([-1,0,1-1/8388608])
    assert decode_pcm(np.array([-32768,0,32767],dtype='<i2').tobytes(),2,1).ravel()==pytest.approx([-1,0,32767/32768])
    assert not decode_pcm(bytes([128]),1,1).flags.writeable


def test_event_metrics_are_one_to_one_and_include_availability_latency():
    metrics=event_metrics([1,2],[{'at':1.01,'available_at':1.12},{'at':1.04,'available_at':1.15},{'at':2.5,'available_at':2.6}],[[0,3]],.075)
    assert (metrics['true'],metrics['false'],metrics['missed'])==(1,2,1)
    assert metrics['available_delay_ms']['median']==pytest.approx(120)
    assert metrics['matches'][0]['timestamp_error_ms']==pytest.approx(10)


def test_region_boundary_accepts_nearby_match_without_counting_external_false_events():
    detections=[{'at':.99,'available_at':1.12},{'at':.98,'available_at':1.15},{'at':.8,'available_at':.9}]
    metrics=event_metrics([1],detections,[[1,2]],.075)
    assert (metrics['true'],metrics['false'],metrics['missed'])==(1,0,0)
    assert metrics['matches'][0]['at']==.99


@pytest.mark.parametrize('changes',[
    {'version':True}, {'kicks':[float('nan')]}, {'kicks':[1,1]}, {'kicks':[4]},
    {'regions':[[1,2],[1.5,3]]}, {'regions':[[0,5]]}, {'bpm':True},
    {'states':[{'start':1,'end':3,'state':'unknown'}]},
    {'states':[{'start':0,'end':2,'state':'groove'},{'start':1,'end':3,'state':'drop'}]},
])
def test_invalid_labels_fail_before_analysis(tmp_path,changes):
    path=labels(tmp_path/'labels.json',**changes)
    with pytest.raises(ValueError):labels_for(path,4)


def test_unannotated_tasks_are_not_treated_as_negative(tmp_path):
    x,_=arrangement('held',duration=3);wav(tmp_path/'audio.wav',x)
    report=replay(tmp_path/'audio.wav',labels(tmp_path/'labels.json',drops=[]))
    assert report['metrics']['kicks'] is None
    assert report['metrics']['drops']['false']==0
    assert report['decision_gates'] and report['physical_output'] is False


def test_replay_is_causal_and_labels_do_not_supply_the_detector_bpm(tmp_path):
    x,truth=arrangement('held',duration=5)
    prefix_frames=512*350;wav(tmp_path/'prefix.wav',x[:prefix_frames]);wav(tmp_path/'full.wav',x)
    first_labels=labels(tmp_path/'prefix.json',bpm=96,kicks=[float(t) for t in truth if t<prefix_frames/48000])
    first=replay(tmp_path/'prefix.wav',first_labels)
    second=replay(tmp_path/'full.wav',labels(tmp_path/'full.json',bpm=150),trace_path=tmp_path/'trace.jsonl')
    until=prefix_frames/48000
    assert first['raw_candidates']==[item for item in second['raw_candidates'] if item['available_at']<=until]
    assert first['confirmed_kicks']==[item for item in second['confirmed_kicks'] if item['available_at']<=until]
    assert first['grid_mode']==second['grid_mode']=='integer'
    assert all(item['available_at']>=item['at'] for item in first['confirmed_kicks'])
    assert first['metrics']['kicks']['true']==len(first['annotations']['kicks'])
    trace=[json.loads(line) for line in (tmp_path/'trace.jsonl').read_text(encoding='utf-8').splitlines()]
    assert trace and all(item['available_at']>=item['at'] for item in trace)


def test_reports_escape_names_and_cli_never_overwrites_existing_directory(tmp_path):
    audio=tmp_path/'audio.wav';x,_=arrangement('isolated',duration=2);wav(audio,x)
    annotation=labels(tmp_path/'labels.json',drops=[])
    output=tmp_path/'report'
    preferences=tmp_path/'preferences.json'
    preferences.write_text(json.dumps(asdict(Settings(beat_grid_mode='manual',beat_fixed_bpm=132,kick_high_hz=140))),encoding='utf-8')
    assert main([str(audio),str(annotation),'--out',str(output),'--settings',str(preferences)])==0
    saved=(output/'report.json').read_bytes()
    assert main([str(audio),str(annotation),'--out',str(output)])==2
    assert (output/'report.json').read_bytes()==saved
    report=json.loads(saved);report['audio']=str(tmp_path/'<script>.wav')
    assert report['grid_mode']=='manual' and report['fixed_bpm']==132
    assert report['analysis_parameters']['kick']['kick_high_hz']==140
    assert '<script>.wav' not in preview(report)
    assert 'Sem rótulos' in preview(report)


def test_truncated_wav_is_an_error_instead_of_silent_success(tmp_path):
    path=tmp_path/'bad.wav';wav(path,np.zeros(4800,dtype=np.float32))
    path.write_bytes(path.read_bytes()[:-50])
    with pytest.raises(ValueError,match='truncado'):
        replay(path,labels(tmp_path/'labels.json'))
