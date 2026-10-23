from dataclasses import asdict, replace
from types import SimpleNamespace
import json
import math
import pytest
from beatlight.contracts import FixtureState, LightingInput, KickEvent
from beatlight.configuration.store import Settings, SettingsStore, validate
from beatlight.core.lighting_runtime import LightingRuntime
from beatlight.lighting.config import LightConfig, LightingControls, PALETTES
from beatlight.lighting.engine import LightingEngine
from beatlight.lighting.fixtures import default_fixtures
from beatlight.lighting.rgbw import preview_rgb, to_rgbw
from test_rhythmic_show import music
from test_lighting_runtime import wait_for

CFG = LightConfig(light_effect="orchestrated_show", light_transition_ms=0)
CONTROLS = LightingControls(CFG, armed=True)


@pytest.mark.parametrize("color", [(1,0,0), (0,1,0), (0,0,1), (1,1,1), (.2,.7,.9), (.95,.97,1), (0,0,0)])
def test_rgbw_preserves_appearance_and_uses_common_white_only(color):
    s = to_rgbw(FixtureState("par", .8, color))
    assert preview_rgb(s) == pytest.approx(color)
    assert s.white == pytest.approx(min(color))
    assert min(s.color) == 0
    assert s.intensity == .8
    assert json.loads(json.dumps(asdict(s)))["white"] == s.white


@pytest.mark.parametrize("strength", [0, .4, 1])
def test_white_control_redistributes_channels_without_changing_palette(strength):
    c = LightingControls(LightConfig(light_palette="gold_ice", light_color_mode="fixed", light_transition_ms=0,
        light_white_strength=strength), armed=True, manual=True)
    f = LightingEngine().render(LightingInput(), c, 0)
    assert f.states[0].white == pytest.approx(.12 * strength)
    assert preview_rgb(f.states[0]) == pytest.approx(PALETTES["gold_ice"][0])


def test_all_default_fixtures_have_white_and_legacy_rgb_still_renders():
    fixtures = default_fixtures()
    assert all("white" in f.capabilities for f in fixtures)
    legacy = replace(fixtures[0], capabilities=("intensity", "rgb"))
    c = LightingControls(LightConfig(light_palette="white", light_transition_ms=0), armed=True, manual=True)
    f = LightingEngine((legacy, fixtures[1])).render(LightingInput(), c, 0)
    assert f.states[0].white == 0 and f.states[0].color == (1,1,1)
    assert f.states[1].white == 1 and f.states[1].color == (0,0,0)


def test_manual_rgbw_channels_are_independent_and_share_the_master_dimmer():
    c = replace(CONTROLS, manual=True, manual_rgbw=True, manual_red=.7, manual_green=.2,
                manual_blue=.1, manual_white=.6, manual_intensity=.5)
    frame = LightingEngine().render(LightingInput(), c, 0)
    for s in frame.states:
        assert s.color == (.7,.2,.1) and s.white == .6
        assert s.intensity == pytest.approx(.4)
    c = replace(c, manual_red=0, manual_green=0, manual_blue=0, manual_white=1)
    pure = LightingEngine().render(LightingInput(), c, 0)
    assert all(s.color == (0,0,0) and s.white == 1 for s in pure.states)


@pytest.mark.parametrize("case", ["blackout", "disabled", "master_zero", "stale", "silence"])
def test_all_four_channels_go_dark_for_priorities_and_audio_loss(case):
    engine = LightingEngine()
    assert any(s.white > .9 for s in engine.render(music(0, state="buildup", tension=.99), CONTROLS, 0).states)
    m, c = music(.1), CONTROLS
    if case == "blackout": c = replace(c, blackout=True)
    if case == "disabled": c = replace(c, armed=False)
    if case == "master_zero": c = replace(c, config=replace(CFG, light_master=0))
    if case == "stale": m = replace(m, audio_fresh=False)
    if case == "silence": m = music(.1, state="silence")
    frame = engine.render(m, c, .1)
    assert all(s.intensity == s.white == 0 and s.color == (0,0,0) for s in frame.states)


def test_rgbw_transition_blends_all_channels_and_blackout_bypasses_it():
    engine = LightingEngine()
    c = replace(CONTROLS, manual=True, manual_rgbw=True, manual_red=1, manual_green=0, manual_blue=0,
                manual_white=0, config=replace(CFG, light_transition_ms=1000))
    engine.render(LightingInput(), c, 0)
    red = engine.render(LightingInput(), c, 1)
    white = replace(c, manual_rgbw=False, config=replace(c.config, light_palette="white"))
    engine.render(LightingInput(), white, 1.1)
    middle = engine.render(LightingInput(), white, 1.6)
    assert 0 < middle.states[0].white < 1
    assert preview_rgb(middle.states[0])[0] == pytest.approx(1)
    assert 0 < preview_rgb(middle.states[0])[1] < 1
    black = engine.render(LightingInput(), replace(white, blackout=True), 1.61)
    assert all(s.white == s.intensity == 0 for s in black.states)


def test_worker_failure_and_stop_cannot_leave_white_channel_latched(monkeypatch):
    controls = LightingControls(LightConfig(light_effect="ambient", light_palette="white", light_transition_ms=0), armed=True, manual=True)
    runtime = LightingRuntime(lambda: (None, SimpleNamespace(state="stopped", audio_age=0)), controls)
    runtime.start()
    try:
        wait_for(lambda: any(s.white == 1 for s in runtime.snapshot().states))
        def fail(*args): raise RuntimeError("rgbw-qa")
        monkeypatch.setattr(runtime.engine, "render", fail)
        wait_for(lambda: runtime.snapshot().status == "error")
        assert all(s.white == s.intensity == 0 and s.color == (0,0,0) for s in runtime.snapshot().states)
    finally:
        runtime.stop()
    assert all(s.white == 0 for s in runtime.snapshot().states)


@pytest.mark.parametrize("white", [-.1, 1.1, math.nan, math.inf, True])
def test_invalid_white_channel_is_rejected(white):
    with pytest.raises(ValueError): FixtureState("par", 1, (0,0,0), white=white)


@pytest.mark.parametrize("field,value", [("light_white_strength",-1), ("light_white_strength",math.nan),
    ("light_white_strength",True), ("light_show_complexity",1.1), ("light_show_complexity",math.inf)])
def test_invalid_new_settings_are_rejected(field, value):
    with pytest.raises(ValueError): LightConfig(**{field:value})


@pytest.mark.parametrize("version", range(1,8))
def test_old_preferences_migrate_with_rgbw_defaults_and_keep_known_fields(version):
    s = validate(dict(version=version, source="wasapi", device_id="saved-realtek", block_size=1024,
        light_white_strength="unknown-before-v8", light_show_complexity="unknown-before-v8"))
    assert s.version == 13 and s.device_id == "saved-realtek" and s.block_size == 1024
    assert s.light_white_strength == 1 and s.light_show_complexity == .7


def test_v8_round_trip_keeps_show_colors_and_audio_tuning(tmp_path):
    s = replace(Settings(), light_effect="orchestrated_show", light_white_strength=.8, light_show_complexity=.9,
                light_palette="cyan_magenta", kick_sensitivity=1.3, beat_min_bpm=100)
    store = SettingsStore(tmp_path / "rgbw.json")
    store.save(s)
    assert store.load() == s


def test_layered_show_repeats_rhythm_then_evolves_at_16_beat_boundary():
    engine = LightingEngine()
    frames = [engine.render(music(i*.5+.01, activity=0), CONTROLS, i*.5+.01) for i in range(24)]
    assert {f.show_pattern for f in frames[:16]} == {"chase"}
    assert frames[16].show_pattern == "bounce"
    for i in range(8):
        assert [s.intensity for s in frames[i].states[:4]] == pytest.approx([s.intensity for s in frames[i+8].states[:4]])
    assert len({tuple(round(c,2) for c in preview_rgb(f.states[0])) for f in frames}) > 6


def test_dense_layered_show_subdivides_and_responds_between_beats():
    engine = LightingEngine()
    a = engine.render(music(.01, density=.9), CONTROLS, .01)
    b = engine.render(music(.26, density=.9), CONTROLS, .26)
    assert a.states[0].intensity > .4 and a.states[1].intensity < .1
    assert b.states[1].intensity - b.states[0].intensity > .3


def test_low_complexity_keeps_single_beat_and_stable_family():
    controls = replace(CONTROLS, config=replace(CFG, light_show_complexity=0))
    engine = LightingEngine()
    frames = [engine.render(music(i*.5+.01, activity=0), controls, i*.5+.01) for i in range(24)]
    assert {f.show_pattern for f in frames} == {"chase"}


def test_layered_fixed_colors_stay_in_palette_and_raw_candidates_do_not_add_white():
    cfg = replace(CFG, light_color_mode="fixed", light_palette="cyan_magenta")
    f = LightingEngine().render(music(.01), replace(CONTROLS, config=cfg), .01)
    assert all(any(preview_rgb(s) == pytest.approx(c) for c in PALETTES["cyan_magenta"]) for s in f.states[:4])
    m = music(.1)
    raw = replace(m, kicks=(KickEvent(.1,.1,1,.95),))
    base = LightingEngine().render(m, CONTROLS, .1)
    assert LightingEngine().render(raw, CONTROLS, .1).states == base.states
    actual = replace(raw, confirmed_kicks=raw.kicks, kick_confirmed_at=.1)
    accented = LightingEngine().render(actual, CONTROLS, .1)
    assert accented.states[0].white > base.states[0].white
