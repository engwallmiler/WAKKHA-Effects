from beatlight.lighting.rgbw import preview_rgb
from dataclasses import replace
import pytest
from beatlight.contracts import KickEvent, KickGridSnapshot, LightingInput, TextureSnapshot
from beatlight.configuration.store import Settings, SettingsStore
from beatlight.lighting.config import LightConfig, LightingControls, PALETTES
from beatlight.lighting.engine import LightingEngine
from beatlight.lighting.show import ShowSequencer
from beatlight.music.grid import grid_clock
from test_musical_lighting import structure

CFG = LightConfig(light_effect="rhythmic_show", light_transition_ms=0)
CONTROLS = LightingControls(CFG, armed=True)


def music(at, state="groove", density=.2, bass=.4, activity=.1, onset=2, tension=.3, grid=True, **kwargs):
    g = KickGridSnapshot(at, "predicting", .5, 0, .9, last_reference_at=0) if grid else None
    s = structure(state, at=at, tension=tension, grid=g, **kwargs)
    t = TextureSnapshot(at, -20, bass, activity, density, density, onset, .3)
    return LightingInput(True, True, structure=s, texture=t, confirmed_kicks=())


def seq(sequence, m, at, cfg=CFG):
    return sequence.render(at=at, beat=grid_clock(m.structure.grid, at), structure=m.structure,
        texture=m.texture, cfg=cfg, palette=PALETTES[cfg.light_palette])


def test_pars_have_visible_spatial_contrast_repeat_and_change_colors_on_grid():
    engine = LightingEngine()
    frames = [engine.render(music(i*.5 + .01), CONTROLS, i*.5 + .01) for i in range(17)]
    for f in frames:
        par = f.states[:4]
        assert max(s.intensity for s in par) - min(s.intensity for s in par) > .35
        assert all(0 <= s.intensity <= .8 for s in f.states)
    for i in range(8):
        for a, b in zip(frames[i].states[:4], frames[i+8].states[:4]):
            assert a.intensity == pytest.approx(b.intensity)
            assert a.color == b.color
    assert frames[0].states[0].color != frames[2].states[0].color
    assert len({max(range(4), key=lambda i: f.states[i].intensity) for f in frames[:4]}) == 4


def test_new_layer_schedules_one_fill_on_next_beat_and_changes_family_at_bar():
    sequence = ShowSequencer()
    first = seq(sequence, music(0), 0)
    assert first.pattern == "chase"
    # Aumento sustentado de densidade e ataques, não apenas um quadro.
    for at in (.1, .2, .3, .49):
        f = seq(sequence, music(at, density=.9, onset=8), at)
        assert f.pattern == "chase" and f.fills == 0
    f = seq(sequence, music(.5, density=.9, onset=8), .5)
    assert f.pattern == "fill" and f.fills == 1 and f.step == 2
    for i in range(31, 121):
        at = i / 60
        f = seq(sequence, music(at, density=.9, onset=8), at)
        assert f.fills == 1
    assert f.pattern == "mirror"  # variation nova, família densa no compasso seguinte


def test_single_attack_or_repeated_texture_snapshot_cannot_schedule_a_fill():
    sequence = ShowSequencer()
    seq(sequence, music(0), 0)
    transient = music(.1, density=.95, onset=10)
    seq(sequence, transient, .1)
    for at in (.2, .3, .49):
        seq(sequence, replace(music(at), texture=transient.texture), at)
    assert seq(sequence, music(.5), .5).fills == 0


def test_pattern_family_is_held_until_bar_and_has_density_hysteresis():
    sequence = ShowSequencer()
    assert seq(sequence, music(0, density=.7), 0).pattern == "pairs"
    assert seq(sequence, music(.5, density=.1), .5).pattern == "pairs"
    for i in range(31, 121):
        at = i / 60
        f = seq(sequence, music(at, density=.6), at)
    assert f.pattern == "pairs"  # .30 mantém família densa, não cruza saída .27


def test_bass_and_density_respond_without_any_confirmed_kick():
    low = LightingEngine().render(music(.275, bass=.05, density=.05, activity=0), CONTROLS, .275)
    high = LightingEngine().render(music(.275, bass=.9, density=.8, activity=.9), CONTROLS, .275)
    assert sum(s.intensity for s in high.states[:4]) > sum(s.intensity for s in low.states[:4]) + .3
    assert high.show_step == 1


def test_unlocked_grid_responds_to_audio_without_claiming_a_step():
    frame = LightingEngine().render(music(0, grid=False, bass=.9, activity=.8), CONTROLS, 0)
    assert frame.show_step == 0 and frame.show_pattern == "acquiring"
    assert max(s.intensity for s in frame.states[:4]) > .3


@pytest.mark.parametrize("state", ["groove", "breakdown", "buildup", "drop"])
def test_operational_priorities_and_audio_freshness_apply_to_show(state):
    m = music(10, state=state)
    for control in (replace(CONTROLS, blackout=True), replace(CONTROLS, armed=False),
                    replace(CONTROLS, config=replace(CFG, light_master=0))):
        assert all(s.intensity == 0 for s in LightingEngine().render(m, control, 10).states)
    manual = LightingEngine().render(m, replace(CONTROLS, manual=True, manual_intensity=.5), 10)
    assert all(s.intensity == pytest.approx(.4) for s in manual.states)
    assert manual.show_pattern == ""
    for bad in (replace(m, audio_fresh=False), replace(m, source_active=False),
                replace(m, structure=replace(m.structure, updated_at=9)),
                replace(m, texture=replace(m.texture, silent=True)), music(10, state="silence")):
        f = LightingEngine().render(bad, CONTROLS, 10)
        assert all(s.intensity == 0 for s in f.states) and f.status == "waiting"


def test_build_has_more_pulses_and_whiter_colors_and_drop_has_stronger_impacts():
    def frames(state, tension):
        engine = LightingEngine()
        return [engine.render(music(i/60, state=state, tension=tension), CONTROLS, i/60) for i in range(120)]
    low, high, drop = frames("breakdown", .2), frames("buildup", .95), frames("drop", .2)
    assert max(s.intensity for f in drop for s in f.states[:4]) > .78
    assert max(s.intensity for f in high for s in f.states[:4]) > max(s.intensity for f in low for s in f.states[:4]) + .4
    assert min(min(preview_rgb(s)) for f in high for s in f.states[:4]) > .9
    # O build acende pares duas vezes por tempo, e não mantém um wash estático.
    brightness = [max(s.intensity for s in f.states[:4]) for f in high]
    peaks = sum(b > .7 and a <= .7 for a, b in zip(brightness, brightness[1:]))
    assert peaks >= 6


def test_fixed_palette_stays_in_its_colors_even_during_build():
    cfg = replace(CFG, light_color_mode="fixed", light_palette="red_blue")
    f = LightingEngine().render(music(0, state="buildup", tension=.99), replace(CONTROLS, config=cfg), 0)
    assert all(any(preview_rgb(s) == pytest.approx(c) for c in PALETTES["red_blue"]) for s in f.states[:4])


def test_raw_bass_candidates_do_not_create_kick_accents():
    m = music(.1)
    reference = LightingEngine().render(m, CONTROLS, .1)
    candidate = replace(m, kicks=(KickEvent(.1, .1, 1, .95),))
    assert LightingEngine().render(candidate, CONTROLS, .1).states == reference.states
    actual = replace(candidate, confirmed_kicks=candidate.kicks, kick_confirmed_at=.1)
    f = LightingEngine().render(actual, CONTROLS, .1)
    assert f.states[0].intensity > reference.states[0].intensity


def test_grid_correction_and_source_gap_cancel_pending_fill():
    for correction in (True, False):
        sequence = ShowSequencer()
        seq(sequence, music(0), 0)
        for at in (.1, .2, .3):
            seq(sequence, music(at, density=.9, onset=8), at)
        at = .5 if correction else 2
        m = music(at, density=.9, onset=8)
        if correction:
            m = replace(m, structure=replace(m.structure, grid=replace(m.structure.grid, revision=1)))
        assert seq(sequence, m, at).fills == 0


def test_show_mode_round_trips_with_existing_audio_and_color_preferences(tmp_path):
    settings = replace(Settings(), light_effect="rhythmic_show", light_color_mode="fixed", kick_sensitivity=1.3)
    store = SettingsStore(tmp_path / "show.json")
    store.save(settings)
    assert store.load() == settings


@pytest.mark.parametrize("state", ["breakdown", "buildup", "drop"])
def test_tension_and_drop_take_priority_over_pending_layer_fill(state):
    sequence = ShowSequencer()
    seq(sequence, music(0), 0)
    for at in (.1, .2, .3):
        seq(sequence, music(at, density=.9, onset=8), at)
    f = seq(sequence, music(.5, state=state, density=.9, onset=8), .5)
    assert f.pattern == state and f.fills == 0
    assert seq(sequence, music(1, density=.9, onset=8), 1).fills == 0


def test_color_control_changes_apply_without_waiting_for_next_bar():
    engine = LightingEngine()
    engine.render(music(.01), CONTROLS, .01)
    cfg = replace(CFG, light_color_mode="fixed", light_palette="red_blue")
    f = engine.render(music(.1), replace(CONTROLS, config=cfg), .1)
    assert all(any(preview_rgb(s) == pytest.approx(c) for c in PALETTES["red_blue"]) for s in f.states[:4])
