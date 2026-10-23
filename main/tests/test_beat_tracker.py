from dataclasses import replace
import math
import numpy as np
import pytest
from beatlight.contracts import KickEvent
from beatlight.music.clock import project_clock
from beatlight.music.config import BeatConfig
from beatlight.music.tracker import BeatTracker


def kick(t, confidence=0.95):
    return KickEvent(float(t), float(t) + 0.025, 0.9, confidence)


def feed(times, tracker=None):
    tracker = tracker or BeatTracker()
    snapshots = []
    for t in times:
        snapshots.append(tracker.process((kick(t),), float(t) + 0.03))
    return tracker, snapshots


@pytest.mark.parametrize("bpm", [90, 120, 128, 138, 160])
def test_constant_tempo_acquires_predicts_and_locks(bpm):
    times = 0.8 + np.arange(30) * 60 / bpm
    tracker, snapshots = feed(times)
    result = snapshots[-1]
    assert result.state == "locked"
    assert result.bpm == pytest.approx(bpm, abs=0.2)
    assert 0 <= result.phase < 1
    assert result.next_beat_at > result.updated_at
    assert abs(result.next_beat_at - (times[-1] + 60 / bpm)) < 0.02
    assert result.confidence > 0.8
    assert result.matched_kicks >= 20
    assert all(a.beat_index <= b.beat_index for a, b in zip(snapshots, snapshots[1:]))
    assert len(tracker._events) <= 32 and len(result.history) <= 120


def test_jitter_and_extra_offbeat_do_not_double_bpm():
    rng = np.random.default_rng(19)
    times = 0.8 + np.arange(36) * 0.5 + rng.uniform(-0.008, 0.008, 36)
    extras = times[8:20:3] + 0.24
    _, snapshots = feed(sorted(np.concatenate((times, extras))))
    result = snapshots[-1]
    assert result.state == "locked"
    assert result.bpm == pytest.approx(120, abs=1)
    assert result.rejected_kicks >= len(extras)
    assert abs(result.phase_error_ms) < 20


def test_gradual_tempo_change_is_followed_without_restarting_clock():
    bpms = np.linspace(120, 135, 90)
    times = [0.8]
    for bpm in bpms:
        times.append(times[-1] + 60 / bpm)
    _, snapshots = feed(times)
    assert snapshots[-1].state == "locked"
    assert snapshots[-1].bpm == pytest.approx(135, abs=1.2)
    assert all(b.beat_index >= a.beat_index for a, b in zip(snapshots, snapshots[1:]))
    assert max(abs(b.bpm - a.bpm) for a, b in zip(snapshots[8:], snapshots[9:])) < 1


def test_missing_kicks_coast_then_recover_without_losing_tempo():
    tracker, snapshots = feed(0.8 + np.arange(15) * 0.5)
    previous = snapshots[-1]
    coast = tracker.process((), previous.last_reference_at + 1.6)
    assert coast.state == "coasting"
    assert coast.confidence < previous.confidence
    assert coast.bpm == pytest.approx(120, abs=0.2)
    assert coast.beat_index > previous.beat_index
    recovered = tracker.process((kick(previous.last_reference_at + 2),), previous.last_reference_at + 2.03)
    assert recovered.state == "locked"
    assert recovered.bpm == pytest.approx(120, abs=0.2)
    assert recovered.beat_index >= coast.beat_index


def test_expiry_stops_predictions_and_does_not_reingest_old_events():
    tracker, snapshots = feed(0.8 + np.arange(12) * 0.5)
    old = snapshots[-1]
    expired = tracker.process(tuple(tracker._events), old.last_reference_at + 4.1)
    assert expired.state == "unlocked"
    assert expired.bpm == 0
    assert expired.next_beat_at is None
    assert expired.confidence == 0
    assert not tracker._events
    new = tracker.process((kick(old.last_reference_at + 5),), old.last_reference_at + 5.03)
    assert new.state == "acquiring" and new.bpm == 0


def test_projection_advances_without_audio_blocks_and_expires():
    _, snapshots = feed(0.8 + np.arange(12) * 0.5)
    original = snapshots[-1]
    projected = project_clock(original, original.updated_at + 1.5)
    assert projected.state == "coasting"
    assert projected.beat_index >= original.beat_index + 2
    expired = project_clock(original, original.expires_at + 0.1)
    assert expired.state == "unlocked" and expired.next_beat_at is None
    assert original.state == "locked"  # não modifica o snapshot publicado


def test_hypotheses_include_half_double_and_range_constraints():
    _, snapshots = feed(0.8 + np.arange(20) * 0.5)
    half, normal, double = snapshots[-1].hypotheses
    assert [h.relation for h in (half, normal, double)] == ["half", "normal", "double"]
    assert half.bpm == pytest.approx(60, abs=0.2)
    assert normal.bpm == pytest.approx(120, abs=0.2)
    assert double.bpm == pytest.approx(240, abs=0.2)
    assert normal.in_range and not half.in_range and not double.in_range
    assert normal.score > double.score


def test_sparse_kicks_keep_half_time_ambiguity_visible():
    _, snapshots = feed(0.8 + np.arange(18) * 1.0)
    result = snapshots[-1]
    assert result.bpm == pytest.approx(120, abs=0.5)
    assert result.ambiguous
    assert result.hypotheses[0].score >= result.hypotheses[1].score


def test_broad_range_prefers_observed_normal_tempo():
    tracker = BeatTracker(BeatConfig(beat_min_bpm=40, beat_max_bpm=240))
    _, snapshots = feed(0.8 + np.arange(20) * 0.5, tracker)
    assert snapshots[-1].bpm == pytest.approx(120, abs=0.5)


def test_double_density_inside_default_range_acquires_half_hypothesis():
    _, snapshots = feed(0.8 + np.arange(32) * 0.25)
    assert snapshots[-1].bpm == pytest.approx(120, abs=0.5)
    assert snapshots[-1].ambiguous


def test_refined_duplicate_kicks_are_not_counted_twice():
    tracker, snapshots = feed(0.8 + np.arange(12) * 0.5)
    before = snapshots[-1]
    event = tracker._events[-1]
    after = tracker.process((replace(event, intensity=0.99),), before.updated_at + 0.01)
    assert after.matched_kicks == before.matched_kicks
    assert after.bpm == before.bpm


def test_random_irregular_events_do_not_claim_stable_sync():
    times = np.cumsum(np.random.default_rng(49).uniform(0.2, 0.9, 50))
    _, snapshots = feed(times)
    assert snapshots[-1].state != "locked"


def test_reset_removes_old_clock_and_history():
    tracker, _ = feed(0.8 + np.arange(12) * 0.5)
    tracker.reset()
    result = tracker.process((), 0.1)
    assert result.state == "unlocked" and result.bpm == 0
    assert not result.hypotheses
    assert result.history == ((0.1, 0.0, 0.0),)


@pytest.mark.parametrize("kwargs", [{"beat_min_bpm": 200}, {"beat_max_bpm": 300},
    {"beat_min_bpm": True}, {"beat_hold_seconds": float("nan")},
    {"beat_hold_seconds": 0}, {"beat_min_bpm": 155}])
def test_invalid_beat_config_rejected(kwargs):
    with pytest.raises(ValueError):
        BeatConfig(**kwargs)


def test_invalid_time_rejected():
    tracker = BeatTracker()
    tracker.process((), 1)
    with pytest.raises(ValueError):
        tracker.process((), 0.5)
    with pytest.raises(ValueError):
        tracker.process((), math.nan)


def test_large_tempo_change_eventually_reacquires():
    old = 0.8 + np.arange(20) * 0.5
    new = old[-1] + np.arange(1, 36) * 60 / 145
    _, snapshots = feed(np.concatenate((old, new)))
    assert snapshots[-1].bpm == pytest.approx(145, abs=1)
    assert snapshots[-1].state == "locked"


def test_unreliable_and_invalid_events_do_not_acquire():
    tracker = BeatTracker()
    events = tuple(kick(i * 0.5, confidence=0.1) for i in range(10))
    events += (kick(math.nan), kick(100), kick(0.1, confidence=math.nan))
    result = tracker.process(events, 6)
    assert result.state == "unlocked" and result.bpm == 0


def test_audio_pipeline_locks_to_detected_kicks():
    from test_kicks import fixture_music, blocks
    from beatlight.dsp.pipeline import AudioAnalyzer
    signal, truth = fixture_music(bpm=128, duration=9)
    analyzer = AudioAnalyzer()
    for block in blocks(signal):
        result = analyzer.process(block)
    assert result.kicks.count == len(truth)
    assert not result.beat_error
    assert result.beat.state == "locked"
    assert result.beat.bpm == pytest.approx(128, abs=0.6)


def test_pipeline_gap_discards_old_beat_clock(block_factory):
    from test_kicks import fixture_music, blocks
    from beatlight.dsp.pipeline import AudioAnalyzer
    analyzer = AudioAnalyzer()
    signal, _ = fixture_music(duration=5)
    for block in blocks(signal):
        before = analyzer.process(block)
    assert before.beat.bpm > 0
    result = analyzer.process(block_factory(np.zeros((512, 1)), sequence=9999))
    assert result.beat.state == "unlocked" and result.beat.bpm == 0
    assert not result.beat.hypotheses


def test_optional_tracker_failure_preserves_kicks_and_spectrum(block_factory, monkeypatch, caplog):
    from beatlight.dsp.pipeline import AudioAnalyzer
    analyzer = AudioAnalyzer()
    def fail(*args):
        raise RuntimeError("tracker-test-failure")
    monkeypatch.setattr(analyzer._beats, "process", fail)
    for seq in range(8):
        result = analyzer.process(block_factory(np.zeros((512, 2)), sequence=seq))
    assert result.beat is None and result.beat_error == "tracker-test-failure"
    assert result.kicks is not None and not result.kick_error
    assert result.spectral is not None and not result.analysis_error
    assert sum(r.message == "beat_tracking_failed" for r in caplog.records) == 1


def test_fractional_range_bounds_are_respected_during_acquisition():
    tracker = BeatTracker(BeatConfig(beat_min_bpm=90.1, beat_max_bpm=110.1))
    _, snapshots = feed(0.8 + np.arange(20) * 60 / 90.2, tracker)
    assert all(not s.bpm or 90.1 <= s.bpm <= 110.1 for s in snapshots)


def test_incomplete_acquisition_expires_without_more_kicks():
    tracker, snapshots = feed([0.8, 1.3, 1.8])
    pending = snapshots[-1]
    assert pending.state == "acquiring" and pending.bpm == 0
    assert project_clock(pending, 6).state == "unlocked"
    old_events = tuple(tracker._events)
    assert tracker.process(old_events, 6).state == "unlocked"
    assert not tracker._events
