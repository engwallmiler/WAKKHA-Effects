from beatlight.lighting.rgbw import preview_rgb
from dataclasses import replace
import pytest
from beatlight.configuration.store import SettingsStore, validate
from beatlight.contracts import LightingInput, StructureSnapshot
from beatlight.lighting.config import LightConfig, LightingControls, PALETTES
from beatlight.lighting.engine import LightingEngine


def music(state, at, tension=0.95):
    return LightingInput(True, True, structure=StructureSnapshot(at, state, tension, 0.9,
        0.5, 0.25, 8, 4, 1, 1, 1, 1 if state == "drop" else 0, 1, at, at, 0.5, "Teste", ()))


def scene(engine, controls, state, start):
    for i in range(120):
        at = start + i / 60
        frame = engine.render(music(state, at), controls, at)
    return frame


def test_automatic_colors_change_audibly_driven_scene_even_for_an_existing_effect():
    controls = LightingControls(LightConfig(light_effect="ambient", light_transition_ms=0), armed=True)
    engine = LightingEngine()
    broken = scene(engine, controls, "breakdown", 10)
    built = scene(engine, controls, "buildup", 12)
    dropped = scene(engine, controls, "drop", 14)
    assert min(preview_rgb(built.states[0])) > 0.9
    assert preview_rgb(broken.states[0])[2] > 0.9 and preview_rgb(broken.states[0])[0] < 0.15
    assert preview_rgb(dropped.states[0])[0] > 0.9 and preview_rgb(dropped.states[0])[2] < 0.2
    assert "breakdown" in broken.color_profile and "drop" in dropped.color_profile


def test_fixed_profile_preserves_selected_palette_during_build_and_drop():
    controls = LightingControls(LightConfig(light_effect="musical", light_color_mode="fixed", light_transition_ms=0), armed=True)
    engine = LightingEngine()
    for state, at in (("breakdown", 10), ("buildup", 12), ("drop", 14)):
        result = scene(engine, controls, state, at)
        assert result.white_mix == 0
        assert preview_rgb(result.states[0]) == pytest.approx(PALETTES["mint_blue"][0])
        assert result.color_profile.startswith("fixo")


def test_auto_build_whitens_and_drop_returns_to_saturated_colors():
    controls = LightingControls(LightConfig(light_effect="musical", light_transition_ms=0), armed=True)
    engine = LightingEngine()
    built = scene(engine, controls, "buildup", 10)
    dropped = scene(engine, controls, "drop", 12)
    assert min(preview_rgb(built.states[0])) > 0.9
    assert preview_rgb(dropped.states[0])[0] > 0.95 and preview_rgb(dropped.states[0])[1] < 0.2
    assert max(f.intensity for f in dropped.states) <= 0.8


def test_manual_color_is_the_selected_palette_even_when_auto_is_enabled():
    controls = LightingControls(LightConfig(light_palette="amber_violet", light_transition_ms=0), armed=True, manual=True)
    result = LightingEngine().render(music("buildup", 10), controls, 10)
    assert preview_rgb(result.states[0]) == pytest.approx(PALETTES["amber_violet"][0])
    assert result.color_profile.startswith("fixo")


def test_v5_migration_preserves_existing_palette_and_enables_explicit_auto_profile():
    settings = validate(dict(version=5, light_palette="amber_violet", light_master=0.65, kick_sensitivity=1.3))
    assert settings.version == 13 and settings.light_color_mode == "automatic"
    assert settings.light_palette == "amber_violet" and settings.light_master == 0.65
    assert settings.kick_sensitivity == 1.3


def test_fixed_preference_survives_round_trip(tmp_path):
    store = SettingsStore(tmp_path / "prefs.json")
    fixed = replace(validate({"version": 6}), light_color_mode="fixed")
    store.save(fixed)
    assert store.load() == fixed
    with pytest.raises(ValueError, match="Perfil de cores"):
        validate(dict(version=6, light_color_mode="unknown"))
