"""A grade procura ataques reais; não fornece notas quando o áudio não as tem."""
import math
import numpy as np
import pytest
from beatlight.contracts import StructureFeatures
from beatlight.music.peak_grid import PeakGridTracker


def feature(at, power, shape=(.9, .3, .1), harmonic=.001):
    norm = math.sqrt(sum(v*v for v in shape))
    db = 10*math.log10(max(power, 1e-12))
    return StructureFeatures(round(at*100), at, db, -50, db, .2, False,
        low_shape=tuple(v/norm for v in shape), bass_db=db,
        harmonic_db=10*math.log10(harmonic))


def run_peaks(kind='regular', period=.5, duration=8,**options):
    tracker = PeakGridTracker()
    matches = []
    for at in np.arange(0, duration, .01):
        distance = (at-.5+period/2)%period-period/2
        pulse = math.exp(-(distance/.018)**2)
        shape = (.9, .3, .1)
        if at > 4:
            if kind=='silence': pulse=0
            if kind=='offgrid': pulse=math.exp(-(((at-.75+period/2)%period-period/2)/.018)**2)
            if kind=='weak': pulse*=.2
            if kind=='spectrum': shape=(.1, .3, .9)
            if kind=='sustained': pulse=1
        matches.extend(tracker.process(feature(float(at), .02+pulse, shape), period, stable=True,**options))
    return tracker, matches


def test_peak_grid_aligns_real_maximum_and_preserves_given_period():
    tracker, matches = run_peaks()
    assert len(matches)>=11
    assert tracker.period == .5 and tracker.ready
    assert all(abs((m.event.occurred_at+.25)%.5-.25)<1e-8 for m in matches)
    assert all(m.event.evidence=='grid-peak' for m in matches)


@pytest.mark.parametrize('kind', ['silence', 'offgrid', 'weak', 'spectrum', 'sustained'])
def test_prediction_cannot_replace_missing_or_incompatible_audio(kind):
    tracker, matches = run_peaks(kind)
    assert not [m for m in matches if m.event.occurred_at>4.1]
    assert tracker.ready and tracker.snapshot(8).state=='predicting'
    assert tracker.snapshot(8).next_peak_at>8


def test_tempo_change_requires_new_acoustic_references():
    tracker, _ = run_peaks()
    tracker.process(feature(8.01,.02),60/130,stable=True)
    assert not tracker.ready and not tracker.references and not tracker.slots


def test_learned_signature_can_acquire_peaks_despite_wrong_old_grid_phase():
    tracker,matches = run_peaks(phase_hint=.15,seed_matches=lambda peak:peak.shape[0]>.9)
    assert tracker.ready and len(matches)>=11
    assert all(abs((m.event.occurred_at+.25)%.5-.25)<1e-8 for m in matches)


def test_four_coherent_peaks_correct_phase_without_reestimating_bpm():
    from beatlight.contracts import KickEvent
    from beatlight.music.config import BeatConfig
    from beatlight.music.grid import KickGrid
    grid = KickGrid(BeatConfig(beat_grid_mode='integer'))
    period = 60/128
    for i in range(16):
        grid.observe(KickEvent(1+i*period,1+i*period,1,.9))
    for i in range(4):
        at = 1+(16+i)*period+.1+(0,.003,-.002,.001)[i]
        matched = grid.reconcile(KickEvent(at,at,1,.9,'grid-peak'),at,phase_only=True)
        if i<3:assert not matched
    assert matched and grid.corrections==1
    assert grid.period==period and grid.tempo_changes==0
    assert grid.matches(KickEvent(at+period,at+period,1,.9),at+period)


def test_peak_memory_is_bounded():
    tracker, matches = run_peaks(duration=60)
    assert len(matches)>100
    assert len(tracker.frames)<=64 and len(tracker.background)<=32
    assert len(tracker.references)<=8 and len(tracker.seeds)<=16
    assert len(tracker.history)<=200 and len(tracker.events)<=16
    assert len(tracker.pending)<=8 and len(tracker.slots)<=1


@pytest.mark.parametrize('bass,frequency,rate,chunk,minimum', [(.95,65,48000,512,22),(1.2,65,48000,512,22),(.95,105,44100,113,21)])
def test_peak_recovery_improves_masked_groove_without_refitting_bpm(bass,frequency,rate,chunk,minimum):
    from beatlight.configuration.store import Settings
    from beatlight.dsp.pipeline import AudioAnalyzer
    from peak_grid_signals import masked_groove
    from test_kicks import blocks
    from kick_masking_signals import event_metrics
    samples,truth = masked_groove(bass=bass,frequency=frequency,rate=rate)
    analyzer = AudioAnalyzer(beat_config=Settings().beat_config())
    confirmed = {}; periods = set()
    for block in blocks(samples,rate=rate,chunk=chunk):
        result = analyzer.process(block)
        assert not result.structure_error and not result.kick_error
        if result.kick_verification:
            confirmed.update((e.occurred_at,e) for e in result.kick_verification.confirmed_events)
        if result.structure and result.structure.grid.tempo_locked:
            periods.add(result.structure.grid.period)
    metrics = event_metrics(confirmed,truth)
    # A 44,1 kHz / 113 amostras o caso 105 Hz preserva os 21 da 0.30;
    # os dois casos 65 Hz precisam melhorar os 20 da referência para 22.
    assert metrics['true']>=minimum and metrics['false']==0, metrics
    if frequency==65:
        assert sum(e.evidence=='grid-peak' for e in confirmed.values())>=2
    assert periods=={60/128} and result.structure.drop_id==0
    assert len(analyzer._structure._identity.peak_pending)<=8


@pytest.mark.parametrize('offbeat', [False,True])
def test_no_recovery_on_predicted_beats_after_kicks_disappear(offbeat):
    from beatlight.configuration.store import Settings
    from beatlight.dsp.pipeline import AudioAnalyzer
    from peak_grid_signals import masked_groove
    from test_kicks import blocks
    samples,_ = masked_groove(bass=.95,remove_kicks=True,offbeat=offbeat)
    analyzer = AudioAnalyzer(beat_config=Settings().beat_config())
    recovered = set()
    for block in blocks(samples):
        result = analyzer.process(block)
        assert not result.structure_error
        if result.kick_verification:
            recovered.update(e.occurred_at for e in result.kick_verification.confirmed_events if e.evidence=='grid-peak')
    assert not [t for t in recovered if t>5]
    assert result.structure.drop_id==0
