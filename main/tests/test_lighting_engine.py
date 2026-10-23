from dataclasses import replace
import math
import pytest
from beatlight.contracts import FixtureState, LightingInput, KickEvent
from beatlight.lighting.config import LightConfig, LightingControls
from beatlight.lighting.engine import LightingEngine
from beatlight.lighting.fixtures import default_fixtures
from beatlight.music.tracker import BeatTracker


def controls(effect="kick_pulse", **kwargs):
    return LightingControls(config=LightConfig(light_effect=effect, light_transition_ms=0, **kwargs), armed=True)


def synchronized():
    tracker = BeatTracker()
    for i in range(12):
        t = 0.5 + i * 0.5
        beat = tracker.process((KickEvent(t, t + 0.02, 1, 0.95),), t)
    assert beat.state == "locked"
    return beat


def test_default_inventory_is_abstract_and_grouped():
    fixtures = default_fixtures()
    assert len(fixtures) == 6
    assert sum(f.kind == "par" for f in fixtures) == 4
    assert sum(f.kind == "moving_head" for f in fixtures) == 2
    assert all(("A" in f.groups) != ("B" in f.groups) for f in fixtures)
    assert all(not hasattr(f, "dmx_address") for f in fixtures)


def test_kick_pulse_uses_acquisition_time_and_decays():
    engine = LightingEngine()
    music = LightingInput(True, True, (KickEvent(10, 10.02, 1, 0.95),))
    cfg = controls()
    peak = engine.render(music, cfg, 10)
    middle = engine.render(music, cfg, 10.12)
    end = engine.render(music, cfg, 10.25)
    assert all(s.intensity == pytest.approx(0.8) for s in peak.states)
    assert all(s.intensity == pytest.approx(0.2) for s in middle.states)
    assert all(s.intensity == 0 for s in end.states)
    # Um evento antigo/refinado não reinicia a duração do pulso.
    refined = replace(music, kicks=(replace(music.kicks[0], intensity=0.9),))
    assert all(s.intensity == 0 for s in engine.render(refined, cfg, 10.3).states)


def test_beat_pulse_projects_clock_without_new_audio_callbacks():
    engine = LightingEngine()
    music = LightingInput(True, False, (), synchronized())
    cfg = controls("beat_pulse")
    peak = engine.render(music, cfg, 6)
    trough = engine.render(music, cfg, 6.3)
    following = engine.render(music, cfg, 6.5)
    coast = engine.render(music, cfg, 7)
    expired = engine.render(music, cfg, 10.1)
    assert peak.states[0].intensity == pytest.approx(0.8)
    assert trough.states[0].intensity == 0
    assert following.states[0].intensity == pytest.approx(0.8)
    assert coast.status == "estimated"
    assert expired.status == "waiting"
    assert all(s.intensity == 0 for s in expired.states)


def test_chase_alternates_groups_by_beat_not_compass():
    engine = LightingEngine()
    music = LightingInput(True, True, (), synchronized())
    cfg = controls("beat_chase")
    first = engine.render(music, cfg, 6.25)
    second = engine.render(music, cfg, 6.75)
    assert first.states[0].intensity != first.states[1].intensity
    assert first.states[0].intensity == pytest.approx(second.states[1].intensity)
    assert first.states[1].intensity == pytest.approx(second.states[0].intensity)


def test_manual_overrides_automation_and_works_without_audio():
    engine = LightingEngine()
    cfg = replace(controls("beat_chase"), manual=True, manual_intensity=0.5, manual_pan=0.8, manual_tilt=0.3)
    result = engine.render(LightingInput(), cfg, 1)
    assert result.status == "manual"
    assert all(s.intensity == pytest.approx(0.4) for s in result.states)
    assert result.states[-1].pan == 0.8
    assert result.states[-1].tilt == 0.3
    assert result.states[0].pan == 0.5


def test_blackout_has_priority_and_remains_latched_across_mode_changes():
    engine = LightingEngine()
    cfg = replace(controls("ambient"), manual=True, blackout=True)
    first = engine.render(LightingInput(), cfg, 1)
    cfg = replace(cfg, config=replace(cfg.config, light_effect="beat_pulse", light_master=1))
    second = engine.render(LightingInput(True, True, (), synchronized()), cfg, 6)
    assert first.status == second.status == "blackout"
    assert first.blackout and second.blackout
    assert all(s.intensity == 0 for s in first.states + second.states)
    released = engine.render(LightingInput(), replace(cfg, blackout=False), 6.1)
    assert released.status == "manual"
    assert released.states[0].intensity == 0.7


def test_disarmed_and_master_zero_cannot_be_bypassed_by_manual():
    engine = LightingEngine()
    cfg = replace(controls("ambient"), armed=False, manual=True)
    assert all(s.intensity == 0 for s in engine.render(LightingInput(), cfg, 0).states)
    cfg = replace(cfg, armed=True, config=replace(cfg.config, light_master=0))
    assert all(s.intensity == 0 for s in engine.render(LightingInput(), cfg, 1).states)


def test_transition_blends_scene_and_blackout_bypasses_fade():
    engine = LightingEngine()
    cfg = LightingControls(LightConfig(light_transition_ms=1000), armed=True, manual=True)
    start = engine.render(LightingInput(), cfg, 0)
    middle = engine.render(LightingInput(), cfg, 0.5)
    end = engine.render(LightingInput(), cfg, 1)
    assert start.states[0].intensity == 0
    assert middle.states[0].intensity == pytest.approx(0.28)
    assert end.states[0].intensity == pytest.approx(0.56)
    changed = replace(cfg, config=replace(cfg.config, light_palette="amber_violet"))
    before = engine.render(LightingInput(), changed, 1.1)
    after = engine.render(LightingInput(), changed, 2.1)
    assert before.states[0].color == end.states[0].color
    assert after.states[0].color != before.states[0].color
    black = engine.render(LightingInput(), replace(changed, blackout=True), 2.11)
    assert all(s.intensity == 0 for s in black.states)


def test_stopping_capture_immediately_removes_automatic_intensity():
    engine = LightingEngine()
    cfg = controls("beat_chase")
    assert any(s.intensity > 0 for s in engine.render(LightingInput(True, True, (), synchronized()), cfg, 6).states)
    stopped = engine.render(LightingInput(), cfg, 6.01)
    assert all(s.intensity == 0 for s in stopped.states)
    assert stopped.status == "waiting"


def test_movement_remains_bounded_and_static_pars_do_not_move():
    engine = LightingEngine()
    cfg = controls("ambient", light_movement_speed=1)
    poses = []
    for at in range(100):
        frame = engine.render(LightingInput(), cfg, float(at))
        assert frame.status == "ambient"
        assert all(0 <= s.intensity <= cfg.config.light_master for s in frame.states)
        assert all(0.15 - 1e-9 <= s.pan <= 0.85 + 1e-9 and 0.3 - 1e-9 <= s.tilt <= 0.7 + 1e-9 for s in frame.states)
        assert all(s.pan == s.tilt == 0.5 for s in frame.states[:4])
        poses.append(frame.states[-1].pan)
    assert max(poses) - min(poses) > 0.5


@pytest.mark.parametrize("kwargs", [{"light_effect": "bad"}, {"light_palette": "bad"},
    {"light_master": True}, {"light_master": 2}, {"light_pulse_ms": 0},
    {"light_transition_ms": -1}, {"light_movement_speed": math.nan}])
def test_invalid_light_config_rejected(kwargs):
    with pytest.raises(ValueError):
        LightConfig(**kwargs)


@pytest.mark.parametrize("kwargs", [{"intensity": math.nan}, {"intensity": 2},
    {"color": (1, 0)}, {"pan": -0.1}, {"tilt": True}])
def test_invalid_fixture_state_rejected(kwargs):
    fields = dict(fixture_id="test", intensity=0.5, color=(1, 0, 0))
    fields.update(kwargs)
    with pytest.raises(ValueError):
        FixtureState(**fields)
