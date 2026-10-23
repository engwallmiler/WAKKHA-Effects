import pytest
from beatlight.contracts import KickEvent
from beatlight.music.grid import KickGrid
from beatlight.music.tracker import BeatTracker


def learned_grid(bpm=120):
    grid, beats = KickGrid(), BeatTracker()
    period = 60 / bpm
    for i in range(40):
        t = 100 + i * period
        event = KickEvent(t, t + 0.02, 1, 0.95)
        beat = beats.process((event,), t + 0.02)
        if not grid.ready or grid.matches(event, t):
            grid.observe(event, beat)
    assert grid.ready
    return grid, beats, t


@pytest.mark.parametrize("bpm", [90, 120, 150])
def test_thirty_second_forecast_preserves_grid_without_inventing_a_kick_or_extending_pll(bpm):
    grid, beats, last = learned_grid(bpm)
    current = grid.snapshot(last + 0.02)
    assert current.forecast_30_at is not None
    assert 30 <= current.forecast_30_at - current.updated_at <= 30 + 60 / bpm
    result = grid.snapshot(last + 30)
    assert result.state == "predicting"
    assert result.confidence > 0.35
    assert result.next_kick_at > last + 30
    assert result.predictions and len(result.predictions) == 8
    assert result.next_kick_at - (last + 30) <= 60 / bpm + 1e-6
    assert all(abs((t - 100) / (60 / bpm) - round((t - 100) / (60 / bpm))) < 0.01 for t in result.predictions)
    assert result.last_reference_at == last
    assert beats.process((), last + 30).state == "unlocked"


def test_offbeat_bass_cannot_reanchor_a_learned_grid():
    grid, _, last = learned_grid()
    anchor = grid.anchor
    for i in range(40):
        t = last + 0.25 + i * 0.5
        assert not grid.matches(KickEvent(t, t, 1, 0.95), t)
    assert grid.anchor == anchor and grid.last_reference == last


def test_learned_clock_continues_after_old_expiry_without_new_kicks():
    grid, _, last = learned_grid()
    result = grid.snapshot(last + 65)
    assert result.state == "predicting"
    assert result.next_kick_at > last + 65
    assert result.predictions and result.horizon_seconds == 60
    assert result.last_reference_at == last


def test_uncertain_timing_is_visible_without_pausing_the_estimated_clock():
    grid, _, last = learned_grid()
    grid.period_error = 0.004
    result = grid.snapshot(last + 30)
    assert result.state == "predicting" and result.predictions
    assert result.uncertainty_ms >= 240
    assert result.confidence < grid.snapshot(last).confidence


def test_grid_tracks_gradual_tempo_change_with_observed_kicks():
    grid, beats, last = learned_grid()
    for i in range(30):
        last += 0.5 - 0.00025 * i
        event = KickEvent(last, last, 1, 0.95)
        assert grid.matches(event, last)
        grid.observe(event, beats.process((event,), last))
    assert 0.49 < grid.period < 0.5
