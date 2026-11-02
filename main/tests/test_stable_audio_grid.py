"""A grade é um prior; somente um ataque acústico pode virar kick."""
from dataclasses import replace
import numpy as np
import pytest
from beatlight.configuration.store import Settings
from beatlight.contracts import KickGridSnapshot, KickEvent
from beatlight.dsp.kicks import KickDetector
from beatlight.dsp.pipeline import AudioAnalyzer
from beatlight.music.config import BeatConfig
from beatlight.music.grid import KickGrid, grid_clock
from kick_masking_signals import event_metrics
from test_kicks import blocks


def early_bass_arrangement(bpm=128, duration=14, rate=48000):
    t = np.arange(round(rate*duration))/rate
    period = 60/bpm
    truth = np.arange(.8, duration-.3, period)
    signal = .015*np.sin(2*np.pi*440*t)
    signal += .4*(1-np.exp(-np.maximum(t-5, 0)/.1))*np.sin(2*np.pi*65*t)
    for onset in truth:
        age = np.maximum(t-onset, 0)
        envelope = np.where(t>=onset, (1-np.exp(-age/.0015))*np.exp(-age/.065), 0)
        phase = 2*np.pi*(52*age+65*.025*(1-np.exp(-age/.025)))
        signal += .7*envelope*np.sin(phase)
        if onset >= 5.5:
            age = np.maximum(t-(onset-.11), 0)
            envelope = np.where(t>=onset-.11, (1-np.exp(-age/.002))*np.exp(-age/.025), 0)
            signal += .9*envelope*np.sin(2*np.pi*110*age)
    return np.asarray(signal*.65, dtype=np.float32), truth


def event(at):
    return KickEvent(at, at, 1, .9)


@pytest.mark.parametrize('bpm', [100, 128, 150])
def test_integer_period_is_exact_and_does_not_wander_with_attack_jitter(bpm):
    grid = KickGrid(BeatConfig(beat_grid_mode='integer'))
    period = 60/bpm
    for i in range(400):
        at = 10+i*period + (0, .004, -.003, .002, -.001)[i%5]
        candidate = event(at)
        if grid.ready:
            assert grid.matches(candidate, at)
        grid.observe(candidate)
        if i >= 7:
            assert grid.tempo_locked
            assert grid.period == 60/bpm
    snapshot = grid.snapshot(at+30)
    assert snapshot.period == period and snapshot.state == 'predicting'
    assert snapshot.tempo_changes == 0
    assert len(grid.observations) <= 32


def test_integer_mode_waits_for_eight_real_observations():
    grid = KickGrid(BeatConfig(beat_grid_mode='integer'))
    for i in range(7):
        grid.observe(event(3+i*60/128))
    assert grid.ready and not grid.tempo_locked
    grid.snapshot(30)
    assert not grid.tempo_locked  # previsão não conta como observação
    grid.observe(event(3+7*60/128))
    assert grid.tempo_locked and grid.period == 60/128


def test_one_hop_latency_shift_does_not_quantize_150_bpm_as_149():
    grid = KickGrid(BeatConfig(beat_grid_mode='integer'))
    for i in range(8):
        grid.observe(event(.8+i*.4+(-.009 if i<2 else .001)))
    assert grid.tempo_locked and grid.period == .4


def test_fixed_bpm_controls_actual_period_instead_of_rounding_a_label():
    grid = KickGrid(BeatConfig(beat_grid_mode='manual', beat_fixed_bpm=128))
    for i in range(20):
        grid.observe(event(1+i*60/127.9))
        if i>=3:
            assert grid.period == 60/128 and grid.tempo_locked
    assert grid.snapshot(50).period == 60/128


def test_integer_grid_accepts_sustained_tempo_change_without_single_hit_chatter():
    grid = KickGrid(BeatConfig(beat_grid_mode='integer'))
    at = 1.
    for _ in range(24):
        grid.observe(event(at)); at += 60/128
    for _ in range(24):
        grid.observe(event(at)); at += 60/130
    assert grid.period == 60/130 and grid.tempo_changes == 1


def test_offbeat_bass_cannot_flip_integer_grid_by_half_a_beat():
    grid = KickGrid(BeatConfig(beat_grid_mode='integer'))
    for i in range(16):
        grid.observe(event(1+i*.5))
    anchor = grid.anchor
    for i in range(24):
        at = 9.25+i*.5
        assert not grid.reconcile(event(at), at)
    assert grid.anchor == anchor and grid.period == .5


def test_consistent_phase_error_can_realign_integer_grid_after_four_real_attacks():
    grid = KickGrid(BeatConfig(beat_grid_mode='integer'))
    for i in range(16):
        grid.observe(event(1+i*.5))
    for i in range(4):
        at = 9.1+i*.5
        accepted = grid.reconcile(event(at), at)
        if i < 3:
            assert not accepted
    assert accepted and grid.corrections == 1 and grid.period == .5
    assert grid.matches(event(11.1), 11.1)


@pytest.mark.parametrize('bpm,gain,rate,chunk', [(100,1,48000,512), (128,1,48000,512), (150,1,48000,512), (128,.1,44100,113)])
def test_stable_audio_only_grid_survives_bass_attacks_before_real_kicks(bpm,gain,rate,chunk):
    samples, truth = early_bass_arrangement(bpm=bpm,rate=rate)
    samples *= gain
    analyzer = AudioAnalyzer(beat_config=Settings().beat_config())
    confirmed = {}; periods = []; guided = False; raw = {}; eligible = {}
    for block in blocks(samples,rate=rate,chunk=chunk):
        result = analyzer.process(block)
        assert not result.structure_error and not result.kick_error
        if result.kick_verification:
            confirmed.update((e.occurred_at, e) for e in result.kick_verification.confirmed_events)
        if result.kicks:
            guided |= result.kicks.grid_guided
            raw.update((e.occurred_at,e) for e in result.kicks.events)
            eligible.update((e.occurred_at,e) for e in result.kicks.eligible_events)
        if result.structure and result.structure.grid.tempo_locked and result.structure.grid.period:
            periods.append(result.structure.grid.period)
    metrics = event_metrics(confirmed, truth)
    assert metrics['true'] == len(truth) and metrics['false'] == 0, metrics
    assert guided and result.kicks.offgrid_count > 0
    assert periods and set(periods) == {60/bpm}
    # Um candidato bruto antecipado não impede outro ataque válido menos de
    # 180 ms depois; a proteção contra duplicar o mesmo kick continua ativa.
    assert any(0 < valid-early < .18 for valid in eligible for early in raw if early not in eligible)
    assert all(b-a >= .18-1e-9 for a,b in zip(sorted(eligible),sorted(eligible)[1:]))
    assert result.structure.drop_id == 0  # o groove não perdeu os kicks de potência total


def reference_clock(at, bpm=128):
    period = 60/bpm
    return grid_clock(KickGridSnapshot(at, 'tracking', period, .82, .95,
        last_reference_at=at, reference_confidence=.95), at)


@pytest.mark.parametrize('kind', ['silence', 'held_bass', 'vibrato'])
def test_grid_does_not_create_kicks_without_a_real_acoustic_attack(kind):
    t = np.arange(48000*4)/48000
    phase = 2*np.pi*65*t
    if kind == 'vibrato':
        phase += .6*np.sin(2*np.pi*5*t)
    samples = np.zeros_like(t) if kind=='silence' else .5*np.sin(phase)
    detector = KickDetector()
    for block in blocks(samples):
        detector.set_clock(reference_clock(block.acquired_at))
        snapshot = detector.push(block)
    assert snapshot.grid_guided and not snapshot.eligible_events and not snapshot.events


def test_stale_clock_is_not_used_as_a_detection_prior():
    detector = KickDetector()
    for block in blocks(np.zeros(48000)):
        detector.set_clock(reference_clock(-10))
        snapshot = detector.push(block)
    assert not snapshot.grid_guided and not snapshot.events


def test_audio_gap_discards_previous_grid_guidance():
    samples, _ = early_bass_arrangement(duration=6)
    analyzer = AudioAnalyzer(beat_config=Settings().beat_config())
    for block in blocks(samples):
        result = analyzer.process(block)
    assert result.kicks.grid_guided
    empty = np.zeros((512, 1), dtype=np.float32)
    block = replace(block, samples=empty, frames=len(empty), acquired_at=6, sequence=block.sequence+1, discontinuity=True)
    result = analyzer.process(block)
    assert result.kicks is None and analyzer._kicks._clock is None
    assert not analyzer._structure._grid.ready


def test_desktop_defaults_to_integer_bpm_and_rejects_invalid_modes():
    assert Settings().beat_config().beat_grid_mode == 'integer'
    for changes in ({'beat_grid_mode': 'unknown'}, {'beat_fixed_bpm':127.9}, {'beat_fixed_bpm':float('nan')}):
        with pytest.raises(ValueError):
            BeatConfig(**changes)
