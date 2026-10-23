from dataclasses import replace
import pytest
from beatlight.contracts import KickEvent, LightingInput, TextureSnapshot
from beatlight.lighting.config import LightConfig, LightingControls
from beatlight.lighting.engine import LightingEngine


def render(effect, bass=0.8, density=0.7, **kwargs):
    controls = LightingControls(LightConfig(light_effect=effect,light_transition_ms=0,**kwargs),armed=True)
    texture = TextureSnapshot(100,-20,bass,0.2,density,density,4,0.3)
    return LightingEngine().render(LightingInput(True,True,texture=texture,confirmed_kicks=()),controls,100)


@pytest.mark.parametrize("effect", ["bass_flow","density_wash"])
def test_new_modes_respond_without_kicks_and_respect_master(effect):
    frame = render(effect)
    assert any(f.intensity > 0.05 for f in frame.states)
    assert all(0 <= f.intensity <= 0.8 for f in frame.states)
    assert all(f.intensity == 0 for f in render(effect,light_master=0).states)


def test_bass_effect_follows_envelope():
    low,high = render("bass_flow",bass=0.1),render("bass_flow",bass=0.9)
    assert min(s.intensity for s in high.states)>max(s.intensity for s in low.states)*2


def test_density_opens_more_fixtures_gradually():
    low,high=render("density_wash",density=0.15),render("density_wash",density=0.9)
    assert sum(s.intensity>0.03 for s in high.states)>sum(s.intensity>0.03 for s in low.states)


@pytest.mark.parametrize("effect",["bass_flow","density_wash"])
def test_new_modes_go_dark_on_stale_audio_and_obey_blackout(effect):
    engine=LightingEngine()
    controls=LightingControls(LightConfig(light_effect=effect,light_transition_ms=0),armed=True)
    texture=TextureSnapshot(100,-20,0.8,0.2,0.7,0.7,4,0.3)
    music=LightingInput(True,True,texture=texture)
    assert all(s.intensity==0 for s in engine.render(music,replace(controls,blackout=True),100).states)
    assert all(s.intensity==0 for s in engine.render(music,controls,101).states)
    assert all(s.intensity==0 for s in engine.render(replace(music,audio_fresh=False),controls,101.1).states)


def test_kick_pulse_uses_confirmed_stream_even_if_raw_bass_candidate_exists():
    controls=LightingControls(LightConfig(light_transition_ms=0),armed=True)
    event=KickEvent(100,100,1,0.95)
    engine=LightingEngine()
    raw_bass=LightingInput(True,True,(event,),confirmed_kicks=())
    assert all(f.intensity==0 for f in engine.render(raw_bass,controls,100).states)
    real=replace(raw_bass,confirmed_kicks=(event,))
    assert any(f.intensity>0 for f in engine.render(real,controls,100.01).states)


@pytest.mark.parametrize("weight",["light_kick_weight","light_bass_weight","light_density_weight"])
def test_weights_reject_invalid_values(weight):
    with pytest.raises(ValueError):
        LightConfig(**{weight:1.1})


def test_multielement_musical_mode_can_light_without_kicks_and_each_weight_can_be_disabled():
    from beatlight.contracts import StructureSnapshot
    state=StructureSnapshot(100,"groove",0,0.9,0.5,0.2,2,3,1,1,1,0,0,None,None,0.5,"test",())
    texture=TextureSnapshot(100,-20,0.8,0.2,0.7,0.7,4,0.3)
    music=LightingInput(True,True,structure=state,texture=texture,confirmed_kicks=())
    controls=LightingControls(LightConfig(light_effect="musical",light_transition_ms=0),armed=True)
    frame=LightingEngine().render(music,controls,100)
    assert min(f.intensity for f in frame.states)>0.15
    disabled=replace(controls,config=replace(controls.config,light_bass_weight=0,light_density_weight=0,light_kick_weight=0))
    assert all(f.intensity==0 for f in LightingEngine().render(music,disabled,100).states)


def test_texture_silence_removes_intensity_immediately():
    controls=LightingControls(LightConfig(light_effect="density_wash",light_transition_ms=0),armed=True)
    texture=TextureSnapshot(100,-120,0.8,0,0.8,0,0,0,silent=True)
    assert all(f.intensity==0 for f in LightingEngine().render(LightingInput(True,True,texture=texture),controls,100).states)


def test_confirmation_delay_does_not_consume_the_visual_pulse():
    controls=LightingControls(LightConfig(light_transition_ms=0),armed=True)
    event=KickEvent(100,100,1,0.95)
    music=LightingInput(True,True,(event,),confirmed_kicks=(event,),kick_confirmed_at=100.12)
    result=LightingEngine().render(music,controls,100.12)
    assert min(f.intensity for f in result.states)>0.7
