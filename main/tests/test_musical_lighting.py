from beatlight.lighting.rgbw import preview_rgb
from dataclasses import replace
import pytest
from beatlight.contracts import KickEvent, LightingInput, MusicalEvent, StructureSnapshot
from beatlight.lighting.config import LightConfig, LightingControls
from beatlight.lighting.engine import LightingEngine


def structure(state="buildup", at=10, tension=0.8, **kwargs):
    fields = dict(updated_at=at, state=state, tension=tension, confidence=0.85, energy=0.5,
        brightness=0.5, onset_rate=6, kick_gap=3, phrase_kick=1, bar_beat=1, phrase_bar=1,
        drop_kicks=1 if state == "drop" else 0, drop_id=1, drop_at=9.8,
        last_kick_at=9.8, period=0.5, reason="Teste", events=(MusicalEvent("breakdown", 5, 0.8, 0.2),))
    fields.update(kwargs)
    return StructureSnapshot(**fields)


def controls(**kwargs):
    return LightingControls(LightConfig(light_effect="musical", light_transition_ms=0), armed=True, **kwargs)


@pytest.mark.parametrize("state", ["breakdown", "buildup", "drop", "groove"])
def test_blackout_and_manual_override_every_musical_state(state):
    music = LightingInput(True, True, (), None, structure(state))
    engine = LightingEngine()
    black = engine.render(music, controls(blackout=True), 10)
    assert all(s.intensity == 0 for s in black.states)
    manual = engine.render(music, controls(manual=True, manual_intensity=0.5), 10.01)
    assert all(s.intensity == pytest.approx(0.4) for s in manual.states)
    assert manual.status == "manual"


def test_stale_audio_or_descriptors_do_not_hold_drop_or_tension():
    engine = LightingEngine()
    s = structure("drop")
    current = LightingInput(True, True, (), None, s)
    assert any(f.intensity > 0.4 for f in engine.render(current, controls(), 10).states)
    stale = engine.render(current, controls(), 10.7)
    assert stale.status == "waiting" and all(f.intensity == 0 for f in stale.states)
    absent = engine.render(replace(current, audio_fresh=False, structure=replace(s, updated_at=11)), controls(), 11)
    assert all(f.intensity == 0 for f in absent.states)
    stopped = engine.render(replace(current, source_active=False), controls(), 12)
    assert all(f.intensity == 0 for f in stopped.states)


def test_drop_is_visibly_stronger_than_breakdown_and_never_exceeds_master():
    engine = LightingEngine()
    first = engine.render(LightingInput(True, True, (), None, structure("breakdown", tension=0.2)), controls(), 10)
    drop = structure("drop", at=10.1, drop_at=10.08)
    second = engine.render(LightingInput(True, True, (KickEvent(10.08, 10.1, 1, 0.9),), None, drop), controls(), 10.1)
    assert min(f.intensity for f in second.states) > max(f.intensity for f in first.states) + 0.3
    assert all(0 <= f.intensity <= 0.8 for f in second.states)
    assert all(f.pan == f.tilt == 0.5 for f in second.states[:4])


def test_missing_structure_and_silence_are_dark():
    engine = LightingEngine()
    assert all(f.intensity == 0 for f in engine.render(LightingInput(True, True), controls(), 10).states)
    silent = engine.render(LightingInput(True, True, (), None, structure("silence", at=11)), controls(), 11)
    assert all(f.intensity == 0 for f in silent.states)


def test_master_zero_remains_absolute_during_drop():
    cfg = controls()
    cfg = replace(cfg, config=replace(cfg.config, light_master=0))
    frame = LightingEngine().render(LightingInput(True, True, (), None, structure("drop")), cfg, 10)
    assert all(f.intensity == 0 for f in frame.states)


def animate(engine, state, start, seconds=2, tension=0.8, **kwargs):
    frames = []
    for i in range(round(seconds * 60)):
        at = start + i / 60
        music = structure(state, at=at, tension=tension, **kwargs)
        frames.append(engine.render(LightingInput(True, True, (), None, music), controls(), at))
    return frames


def test_build_up_accelerates_whitens_and_brightens_before_drop():
    engine = LightingEngine()
    low = animate(engine, "breakdown", 10, tension=0.2)[-1]
    early = animate(engine, "buildup", 12, tension=0.25)[-1]
    high = animate(engine, "buildup", 14, tension=0.95, roll_strength=1)[-1]
    assert high.movement_hz > early.movement_hz * 1.8
    assert high.white_mix > 0.9
    assert min(min(preview_rgb(s)) for s in high.states) > 0.9
    assert min(s.intensity for s in high.states) > max(s.intensity for s in low.states) + 0.25
    assert all(s.intensity <= high.master for s in high.states)


def test_movement_has_continuous_phase_through_tension_changes_and_cycle_wraps():
    engine = LightingEngine()
    poses = []
    for i in range(20 * 60):
        at = 50000 + i / 60
        state = "groove" if i < 120 else "buildup" if i < 360 else "drop" if i < 600 else "groove"
        tension = (0.2 if (i // 30) % 2 == 0 else 0.95) if state == "buildup" else 0.5
        music = structure(state, at=at, tension=tension, drop_kicks=3)
        frame = engine.render(LightingInput(True, True, (), None, music), controls(), at)
        poses.append((frame.states[-1].pan, frame.states[-1].tilt))
    assert max(abs(b[j] - a[j]) for a, b in zip(poses, poses[1:]) for j in range(2)) < 0.045
    assert max(p[0] for p in poses) - min(p[0] for p in poses) > 0.5


def test_zero_movement_limit_freezes_pose_even_when_structure_changes():
    engine = LightingEngine()
    previous = animate(engine, "buildup", 10)[-1]
    cfg = controls()
    cfg = replace(cfg, config=replace(cfg.config, light_movement_speed=0))
    for i in range(120):
        at = 12 + i / 60
        current = engine.render(LightingInput(True, True, (), None, structure("drop", at=at)), cfg, at)
        assert current.movement_hz == 0
        assert [(s.pan, s.tilt) for s in current.states] == [(s.pan, s.tilt) for s in previous.states]


def test_drop_returns_to_palette_and_changes_color_group_after_four_kicks():
    engine = LightingEngine()
    first = animate(engine, "drop", 10, drop_kicks=1)[-1]
    following = animate(engine, "drop", 12, drop_kicks=5)[-1]
    assert first.states[0].color[0] > first.states[0].color[2]
    assert following.states[0].color[2] > following.states[0].color[1]
    assert following.white_mix < 0.1
    assert min(s.intensity for s in following.states) >= 0.5


def test_metadata_clears_when_automatic_effect_has_no_reference_or_is_overridden():
    engine = LightingEngine()
    animate(engine, "buildup", 10)
    stopped = engine.render(LightingInput(), controls(), 12)
    assert stopped.movement_hz == stopped.white_mix == 0
    manual = engine.render(LightingInput(), controls(manual=True), 13)
    assert manual.movement_hz == 0
