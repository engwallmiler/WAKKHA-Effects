"""Regressão do problema de mascaramento; não mede acurácia em faixas reais."""
import numpy as np
import pytest
from beatlight.dsp.pipeline import AudioAnalyzer
from beatlight.dsp.kicks import KickDetector
from kick_masking_signals import arrangement,event_metrics
from test_kicks import blocks,detect


@pytest.mark.parametrize('kind',['isolated','held','offbeat','compressed'])
def test_masked_kicks_reach_structure_without_confirming_offbeat_bass(kind):
    x,truth=arrangement(kind);analyzer=AudioAnalyzer();confirmed={};acquired=None
    for block in blocks(x):
        result=analyzer.process(block)
        assert not result.kick_error and not result.structure_error and not result.kick_verification_error
        if result.kick_verification:
            for event in result.kick_verification.confirmed_events:confirmed[event.occurred_at]=event
        if result.structure and result.structure.grid.period and acquired is None:acquired=result.structure.updated_at
    metrics=event_metrics(confirmed,truth)
    assert metrics['true']==len(truth) and metrics['false']==0,metrics
    assert acquired<2.6
    assert result.structure.grid.period==pytest.approx(.5,abs=.006)
    assert max(result.kicks.masked_history,key=lambda point:point[1])[1]>0
    assert len(analyzer._kicks._masked.history)<=200
    assert len(analyzer._kicks._masked.scores)<=100
    assert len(analyzer._structure._identity.reference_events)<=16


@pytest.mark.parametrize('rate,gain,chunk',[(44100,.2,113),(48000,1,512),(48000,.05,2048)])
def test_masked_sensor_is_stereo_phase_safe_gain_invariant_and_streaming(rate,gain,chunk):
    x,truth=arrangement('held',rate=rate,duration=4,gain=gain)
    detector,events=detect(np.column_stack((x,-x)),rate,chunk)
    metrics=event_metrics([event.occurred_at for event in events],truth)
    assert metrics['true']==len(truth) and metrics['false']==0,metrics
    assert detector.latest.masked_count>=len(truth)-1
    assert len(detector._masked.previous)<=2 and len(detector._pending)<2048


def test_masked_sensor_does_not_turn_vibrato_into_repeated_kicks():
    rate=48000;t=np.arange(rate*4)/rate
    phase=2*np.pi*(65*t+3/(2*np.pi*5)*np.sin(2*np.pi*5*t))
    detector,events=detect(.5*np.sin(phase))
    assert not events


def test_reset_discards_spectral_background_and_recent_proposals():
    x,_=arrangement('held',duration=2);detector=KickDetector()
    for block in blocks(x):detector.push(block)
    detector.reset()
    assert detector.latest is None
    for block in blocks(np.zeros(48000,dtype=np.float32)):snapshot=detector.push(block)
    assert snapshot.masked_count==0 and not snapshot.events
    assert all(score==0 for _,score,_ in snapshot.masked_history)


def test_subtracted_tail_under_bass_is_uncertain_instead_of_infinite_decay():
    from beatlight.music.kick_identity import KickIdentity
    from beatlight.contracts import StructureFeatures
    values=[]
    for gain_db in (0,-20,-34):
        identity=KickIdentity()
        for i,age in enumerate((-.09,-.07,-.05,-.03,0,.02,.04,.05)):
            db=(-7 if 0<=age<=.02 else -10)+gain_db
            identity.history.append(StructureFeatures(i,1+age,db,-60,db,.1,False,low_shape=(.6,.8),bass_db=db))
        descriptor=identity._describe(1,early=True)
        assert descriptor is not None and 0<=descriptor.early_decay<=30
        values.append(descriptor.early_decay)
    assert max(values)-min(values)<1e-6


@pytest.mark.parametrize('bpm',[100,128,150])
def test_offbeat_bass_does_not_steal_the_grid_at_other_tempos(bpm):
    x,truth=arrangement('offbeat',bpm=bpm);analyzer=AudioAnalyzer();confirmed={}
    for block in blocks(x):
        snapshot=analyzer.process(block)
        if snapshot.kick_verification:
            for event in snapshot.kick_verification.confirmed_events:confirmed[event.occurred_at]=event
    metrics=event_metrics(confirmed,truth)
    assert metrics['true']==len(truth) and metrics['false']==0,metrics
    assert snapshot.structure.grid.period==pytest.approx(60/bpm,abs=.006)
