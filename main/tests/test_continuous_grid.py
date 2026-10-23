from collections import deque
from dataclasses import replace
import pytest
from beatlight.contracts import KickEvent, StructureFeatures
from beatlight.music.config import BeatConfig
from beatlight.music.grid import KickGrid, project_grid, grid_clock
from beatlight.music.structure import StructureTracker


def kick(t):
    return KickEvent(t, t + 0.02, 1, 0.95)


def four(period=0.5, config=None):
    grid = KickGrid(config)
    for i in range(4):
        grid.observe(kick(100 + i * period))
    assert grid.ready
    return grid


@pytest.mark.parametrize("bpm", [90, 120, 150])
def test_four_regular_audio_attacks_acquire_without_waiting_for_pll(bpm):
    grid = four(60 / bpm)
    snap = grid.snapshot(grid.last_reference + 0.12)
    assert 60 / snap.period == pytest.approx(bpm)
    assert snap.observations == 4
    assert snap.confidence > 0.6


def test_irregular_attacks_do_not_acquire_and_bpm_preference_is_respected():
    grid = KickGrid()
    for t in [100, 100.5, 101.15, 101.4]:
        grid.observe(kick(t))
    assert not grid.ready
    for i in range(4):
        grid.observe(kick(110 + i * 0.25))
    assert not grid.ready
    assert four(0.3, BeatConfig(160, 220)).ready


def test_clock_and_phrase_continue_for_two_minutes_without_inventing_events():
    grid = four()
    before = grid.last_reference
    for elapsed in [0.2, 2.2, 30.2, 120.2]:
        snap = project_grid(grid.snapshot(before), before + elapsed)
        assert snap.beat_index == 3 + int(elapsed / 0.5)
        assert snap.phase == pytest.approx(0.4)
        assert snap.forecast_30_at >= snap.updated_at + 30 - 1e-7
        assert grid_clock(snap, snap.updated_at).period == 0.5
    assert grid.last_reference == before and len(grid.observations) == 4
    assert snap.state == "predicting" and snap.uncertainty_ms > 4


def test_single_offgrid_attack_and_irregular_roll_cannot_realign():
    grid = four()
    anchor = grid.anchor
    assert not grid.reconcile(kick(103.2), 103.32)
    for t in [103.31, 103.39, 103.56, 103.62, 103.73, 103.81]:
        assert not grid.reconcile(kick(t), t + 0.12)
    assert grid.anchor == anchor and grid.corrections == 0


def test_four_displaced_real_kicks_correct_phase_then_follow_the_new_grid():
    grid = four()
    old_index = grid.snapshot(103.2).beat_index
    for i in range(4):
        t = 103.2 + i * 0.5
        accepted = grid.reconcile(kick(t), t + 0.12)
        if i < 3:
            assert not accepted
    assert accepted and grid.corrections == grid.revision == 1
    result = grid.snapshot(t + 0.12)
    assert result.last_correction_ms == pytest.approx(200)
    assert result.beat_index >= old_index
    assert result.phase == pytest.approx(0.24)
    assert grid.matches(kick(t + 0.5), t + 0.62)
    assert not grid.matches(kick(t + 0.25), t + 0.37)


def test_consistent_large_tempo_change_can_reacquire_and_missing_kicks_do_not_halve_bpm():
    grid = four()
    for i in range(4):
        t = 104.2 + i * 0.4
        accepted = grid.reconcile(kick(t), t + 0.12)
    assert accepted and grid.period == pytest.approx(0.4)
    grid = four()
    for i in range(4):
        t = 104.2 + i
        accepted = grid.reconcile(kick(t), t + 0.12)
    assert accepted and grid.period == 0.5


def test_structure_leaves_learning_after_four_kicks_and_phrase_advances_without_kick():
    tracker = StructureTracker()
    events = deque(maxlen=16)
    snapshots = []
    for i in range(301):
        at = 100 + i * 0.02
        if i in (0, 25, 50, 75):
            events.append(kick(at))
        snapshots.append(tracker.process(StructureFeatures(i, at, -20, -35, -15, 0.3, False), tuple(events)))
    first = next(s for s in snapshots if s.state == "groove")
    assert first.updated_at <= 101.62
    no_kicks = [s for s in snapshots if 102 <= s.updated_at < 106]
    assert len({s.phrase_kick for s in no_kicks}) == 8
    assert len(no_kicks[-1].confirmed_kicks) == 4
    assert no_kicks[-1].drop_id == no_kicks[-1].drop_kicks == 0


def test_phrase_restarts_at_drop_reference_and_projection_has_same_phase_everywhere():
    grid = four()
    grid.reset_phrase(106)
    snap = grid.snapshot(106.1)
    assert (snap.beat_index - snap.phrase_origin) % 8 + 1 == 1
    projected = project_grid(snap, 107.6)
    clock = grid_clock(snap, 107.6)
    assert clock.phase == projected.phase == pytest.approx(0.2)
    assert clock.beat_index == projected.beat_index
    assert (projected.beat_index - projected.phrase_origin) % 8 + 1 == 4
    assert projected.next_phrase_at == pytest.approx(110)


@pytest.mark.parametrize("effect", ["beat_pulse", "beat_chase"])
def test_grid_drives_clock_effects_after_pll_expires_with_no_acoustic_kick(effect):
    from beatlight.contracts import LightingInput, StructureSnapshot
    from beatlight.lighting.config import LightConfig, LightingControls
    from beatlight.lighting.engine import LightingEngine
    grid = four()
    at = 130.02
    snap = grid.snapshot(at)
    structure = StructureSnapshot(at, "breakdown", 0.2, 0.8, 0.2, 0.3, 0, 28.52,
        5, 1, 2, 0, 0, None, 101.5, 0.5, "teste", (), grid=snap)
    controls = LightingControls(LightConfig(light_effect=effect, light_transition_ms=0), armed=True)
    engine = LightingEngine()
    result = engine.render(LightingInput(True, True, structure=structure, confirmed_kicks=()), controls, at)
    assert result.status == "estimated"
    assert max(s.intensity for s in result.states) > 0.4
    dark = engine.render(LightingInput(False, False, structure=structure), controls, at + 0.02)
    assert all(s.intensity == 0 for s in dark.states)


def test_audio_pipeline_acquires_after_four_detected_kicks_before_three_seconds():
    import numpy as np
    from beatlight.audio.demo import structure_demo_samples
    from beatlight.contracts import AudioBlock
    from beatlight.dsp.pipeline import AudioAnalyzer
    analyzer = AudioAnalyzer()
    learned = None
    for seq, first in enumerate(range(0, 48000 * 3, 512)):
        t = np.arange(first, first + 512) / 48000
        samples = structure_demo_samples(t)
        samples.setflags(write=False)
        at = 100 + first / 48000
        result = analyzer.process(AudioBlock("fast-acquire", samples, 48000, 2, seq, 512, at, at + 512 / 48000))
        if result.structure and result.structure.reference_ready:
            learned = result
            break
    assert learned is not None
    assert learned.structure.updated_at < 102.5
    assert len(learned.structure.confirmed_kicks) == 4
    assert not learned.structure_error and not learned.kick_verification_error


def test_grid_clock_can_be_projected_without_an_expiry_or_double_counting():
    from beatlight.music.clock import project_clock
    grid = four()
    original = grid.snapshot(104.1)
    projected = project_clock(grid_clock(original, 104.1), 109.1)
    expected = grid_clock(original, 109.1)
    assert projected.phase == pytest.approx(expected.phase)
    assert projected.beat_index == expected.beat_index
    assert projected.confidence == pytest.approx(expected.confidence)


def test_weaker_identity_candidates_cannot_propose_a_grid_correction():
    grid = four()
    for i in range(8):
        t = 104.25 + i * 0.5
        assert not grid.reconcile(kick(t), t + 0.12, allow_correction=False)
    assert grid.corrections == 0 and grid.anchor == 100


def test_real_shifted_kicks_realign_audio_pipeline_without_waiting_for_pll():
    import numpy as np
    from beatlight.audio.demo import structure_demo_samples
    from beatlight.contracts import AudioBlock
    from beatlight.dsp.pipeline import AudioAnalyzer
    analyzer = AudioAnalyzer()
    corrected = None
    for seq, first in enumerate(range(0, 48000 * 16, 512)):
        t = np.arange(first, first + 512) / 48000
        samples = structure_demo_samples(t)
        env = np.exp(-(((t - 0.2) * 2) % 1) * 12) * (t >= 12)
        samples[:, 0] += (0.45 * env * np.sin(2 * np.pi * 70 * t)).astype(np.float32)
        samples[:, 1] += (0.4 * env * np.sin(2 * np.pi * 85 * t)).astype(np.float32)
        samples.setflags(write=False)
        at = 100 + first / 48000
        result = analyzer.process(AudioBlock("shifted-kick", samples, 48000, 2, seq, 512, at, at + 512 / 48000))
        if result.structure and result.structure.grid.corrections:
            corrected = result
            break
    assert corrected is not None
    assert corrected.structure.grid.corrections == 1
    assert corrected.structure.grid.last_correction_ms == pytest.approx(200, abs=25)
    assert corrected.structure.updated_at < 115
    assert not corrected.structure_error
