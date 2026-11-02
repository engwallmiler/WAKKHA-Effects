"""Regressão do perfil que rejeitava indefinidamente ataques fortes na grade."""
import numpy as np
import pytest
from beatlight.configuration.store import Settings
from beatlight.contracts import KickGridSnapshot
from beatlight.dsp.kicks import KickDetector
from beatlight.dsp.pipeline import AudioAnalyzer
from beatlight.music.grid import grid_clock
from kick_masking_signals import event_metrics
from recurrent_profile_signals import changed_kick_scene
from test_kicks import blocks


@pytest.mark.parametrize('restart_at,rate,chunk',[(5,48000,512),(9,48000,512),(5,44100,113)])
def test_aligned_new_kick_timbre_relearns_profile_and_restores_confirmations(restart_at,rate,chunk):
    samples,truth=changed_kick_scene(restart_at=restart_at,rate=rate)
    settings=Settings(kick_high_hz=110)
    analyzer=AudioAnalyzer(beat_config=settings.beat_config(),kick_config=settings.kick_config())
    events={};periods=set();first_recovery=None
    for block in blocks(samples,rate=rate,chunk=chunk):
        r=analyzer.process(block)
        assert not any((r.kick_error,r.structure_error,r.kick_verification_error))
        if r.kick_verification:
            events.update((e.occurred_at,e) for e in r.kick_verification.confirmed_events)
            if r.kick_verification.kick_recovery.relearns and first_recovery is None:
                first_recovery=block.acquired_at
        if r.structure and r.structure.grid.tempo_locked:periods.add(r.structure.grid.period)
    metrics=event_metrics(events,truth)
    assert metrics['false']==0 and metrics['missed']<=5,metrics
    assert first_recovery is not None and first_recovery<restart_at+2.6
    assert r.structure.kick_recovery.relearns>=1
    assert any(e.evidence=='grid-profile' for e in events.values())
    assert r.structure.state=='groove' and r.structure.drop_id==0
    assert periods=={60/127}
    assert len(analyzer._structure._identity.recurrent.candidates)<=4
    assert len(analyzer._structure._identity.recurrent.offgrid)<=8
    # A referência antiga tem shape incompatível; a retomada deve ocorrer
    # apesar dela, e os kicks seguintes passam pela confirmação normal.
    later=truth[truth>restart_at+3]
    assert all(any(abs(t-onset)<=.075 for t in events) for onset in later)


@pytest.mark.parametrize('kind',['held','offbeat','harmonic','roll'])
def test_recurrent_profile_does_not_learn_bass_or_double_time_roll(kind):
    samples,truth=changed_kick_scene(kind=kind)
    analyzer=AudioAnalyzer(beat_config=Settings().beat_config());events={}
    for block in blocks(samples):
        r=analyzer.process(block)
        assert not r.structure_error
        if r.kick_verification:events.update((e.occurred_at,e) for e in r.kick_verification.confirmed_events)
    assert r.structure.kick_recovery.relearns==0
    assert not any(e.evidence=='grid-profile' for e in events.values())
    assert r.structure.drop_id==0
    # Os dois candidatos do início do roll já eram aprovados pela versão 0.31.
    assert event_metrics(events,truth)['false']<=(2 if kind=='roll' else 0)


@pytest.mark.parametrize('kind',['silence','held','vibrato'])
def test_predictive_grid_at_forty_percent_remains_prior_without_fabricating_events(kind):
    detector=KickDetector();t=np.arange(48000*3)/48000
    phase=2*np.pi*65*t+(.6*np.sin(2*np.pi*5*t) if kind=='vibrato' else 0)
    samples=np.zeros_like(t) if kind=='silence' else .4*np.sin(phase)
    for block in blocks(samples):
        grid=KickGridSnapshot(block.acquired_at,'predicting',60/127,.8,.4,
            last_reference_at=-400,reference_confidence=.4,tempo_locked=True,tempo_mode='integer')
        detector.set_clock(grid_clock(grid,block.acquired_at),stable_grid=True)
        snapshot=detector.push(block)
    assert snapshot.grid_guided and not snapshot.events


def test_unverified_low_confidence_clock_does_not_get_stable_grid_exception():
    detector=KickDetector()
    for block in blocks(np.zeros(48000)):
        grid=KickGridSnapshot(block.acquired_at,'predicting',60/127,.8,.4,last_reference_at=-400,reference_confidence=.4)
        detector.set_clock(grid_clock(grid,block.acquired_at))
        snapshot=detector.push(block)
    assert not snapshot.grid_guided
