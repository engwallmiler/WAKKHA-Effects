from dataclasses import replace
import pytest
from beatlight.contracts import LightingInput
from beatlight.lighting.config import EFFECTS, LightConfig, LightingControls
from beatlight.lighting.engine import LightingEngine
from test_rhythmic_show import music


@pytest.mark.parametrize("effect", EFFECTS)
@pytest.mark.parametrize("state", ["groove", "breakdown", "buildup", "drop"])
def test_moving_heads_light_and_move_as_a_pair_in_every_automatic_effect(effect, state):
    engine = LightingEngine()
    controls = LightingControls(LightConfig(light_effect=effect, light_transition_ms=300), armed=True)
    for i in range(91):
        at = i/60
        frame = engine.render(music(at, state=state, density=.8, tension=.9, drop_kicks=4), controls, at)
        a, b = frame.states[-2:]
        assert a.intensity == pytest.approx(b.intensity)
        assert a.color == b.color and a.white == b.white
        assert a.pan + b.pan == pytest.approx(1)
        assert a.tilt == pytest.approx(b.tilt)


def test_pair_remains_coordinated_during_mode_transition_from_manual():
    engine = LightingEngine()
    controls = LightingControls(LightConfig(light_effect="phrase_show"), armed=True, manual=True,
        manual_pan=.8, manual_tilt=.2)
    engine.render(LightingInput(), controls, 0)
    manual = engine.render(LightingInput(), controls, .4)
    assert [s.pan for s in manual.states[-2:]] == [.8, .8]
    controls = replace(controls, manual=False)
    for i in range(1,31):
        at = .4+i/60
        frame = engine.render(music(at), controls, at)
        a,b = frame.states[-2:]
        assert a.intensity == b.intensity and a.color == b.color and a.white == b.white
        assert a.pan + b.pan == pytest.approx(1) and a.tilt == b.tilt


def test_zero_speed_keeps_positions_and_blackout_and_master_still_apply():
    engine = LightingEngine()
    controls = LightingControls(LightConfig(light_effect="musical", light_transition_ms=0), armed=True)
    frame = engine.render(music(0), controls, 0)
    for i in range(1,10): frame = engine.render(music(i/60), controls, i/60)
    frozen = [(s.pan,s.tilt) for s in frame.states[-2:]]
    controls = replace(controls,config=replace(controls.config,light_movement_speed=0))
    for i in range(10,30):
        frame = engine.render(music(i/60),controls,i/60)
        assert [(s.pan,s.tilt) for s in frame.states[-2:]] == frozen
    dark = engine.render(music(.6),replace(controls,blackout=True),.6)
    assert all(s.intensity == s.white == 0 for s in dark.states)
    zero = engine.render(music(.7),replace(controls,config=replace(controls.config,light_master=0)),.7)
    assert all(s.intensity == s.white == 0 for s in zero.states)
