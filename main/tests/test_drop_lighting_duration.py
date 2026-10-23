from dataclasses import replace
import pytest
from beatlight.lighting.engine import LightingEngine
from beatlight.lighting.config import LightConfig, LightingControls
from test_rhythmic_show import music


@pytest.mark.parametrize("effect", ["rhythmic_show", "orchestrated_show", "phrase_show"])
def test_drop_pulse_cannot_inherit_half_beat_subdivision(effect):
    controls = LightingControls(LightConfig(light_effect=effect, light_transition_ms=0), armed=True)
    dense, direct = LightingEngine(), LightingEngine()
    dense.render(music(0, density=.95), controls, 0)
    m = music(.26, state="drop", density=.95, drop_kicks=1)
    a = dense.render(m, controls, .26)
    b = direct.render(m, controls, .26)
    assert [s.intensity for s in a.states[:4]] == pytest.approx([s.intensity for s in b.states[:4]])
    assert max(s.intensity for s in a.states[:4]) > .4


@pytest.mark.parametrize("effect", ["musical", "rhythmic_show", "orchestrated_show", "phrase_show"])
def test_lighting_preserves_drop_for_all_eight_confirmed_positions(effect):
    engine = LightingEngine()
    c = LightingControls(LightConfig(light_effect=effect, light_transition_ms=0), armed=True)
    for i in range(8):
        at = i*.5+.01
        f = engine.render(music(at, state="drop", drop_kicks=i+1, density=.95), c, at)
        assert f.status == "drop" and max(s.intensity for s in f.states[:4]) > .65
