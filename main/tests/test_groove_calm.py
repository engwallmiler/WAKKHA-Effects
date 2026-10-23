from dataclasses import replace
import math
import pytest
from beatlight.lighting.config import LightConfig,LightingControls,PALETTES
from beatlight.lighting.engine import LightingEngine
from beatlight.lighting.movers import MOVER_STYLES
from beatlight.lighting.breakdown import BREAKDOWN_STYLES
from beatlight.lighting.rgbw import preview_rgb
from beatlight.configuration.store import Settings,SettingsStore,validate
from test_rhythmic_show import music

CFG=LightConfig(light_effect="phrase_show",light_transition_ms=0,light_phrase_prepare="none")
C=LightingControls(CFG,armed=True)


@pytest.mark.parametrize("style",list(MOVER_STYLES))
def test_movers_share_rhythm_color_and_pose_and_repeat_in_eight(style):
    engine=LightingEngine()
    c=replace(C,config=replace(CFG,light_mover_pattern=style))
    frames=[engine.render(music(i*.25+.01),c,i*.25+.01) for i in range(32)]
    for f in frames:
        a,b=f.states[-2:]
        assert a.intensity==b.intensity and a.color==b.color and a.white==b.white
        assert a.pan+b.pan==pytest.approx(1) and a.tilt==b.tilt
    for a,b in zip(frames,frames[16:]):
        assert a.states[-1].intensity==pytest.approx(b.states[-1].intensity)
        assert preview_rgb(a.states[-1])==pytest.approx(preview_rgb(b.states[-1]))
    assert len({tuple(round(x,2) for x in preview_rgb(f.states[-1])) for f in frames[:16]})>=4
    assert max(f.states[-1].intensity for f in frames)-min(f.states[-1].intensity for f in frames)>.2


def test_automatic_mover_rhythm_changes_with_par_context_and_remains_held_in_stable_cycle():
    engine=LightingEngine()
    rhythms=[]
    for i in range(721):
        at=i/60
        f=engine.render(music(at,density=.9 if at>=1.1 else .2),C,at)
        rhythms.append(f.mover_rhythm)
    assert len(set(rhythms[:240]))==1
    assert len(set(rhythms[240:]))==1 and rhythms[0]!=rhythms[240]


def test_fixed_mover_palette_has_no_automatic_hue_rotation():
    c=replace(C,config=replace(CFG,light_color_mode="fixed",light_palette="cyan_magenta"))
    engine=LightingEngine()
    for i in range(16):
        at=i*.25
        f=engine.render(music(at),c,at)
        assert any(preview_rgb(f.states[-1])==pytest.approx(color) for color in PALETTES["cyan_magenta"])


@pytest.mark.parametrize("style",list(BREAKDOWN_STYLES))
@pytest.mark.parametrize("period",[.4,.66])
def test_calm_pars_fade_slowly_and_ignore_grid_speed(style,period):
    c=replace(C,config=replace(CFG,light_breakdown_style=style))
    engine=LightingEngine()
    frames=[]
    for i in range(720):
        at=i/60
        m=music(at,state="breakdown",tension=.2)
        m=replace(m,structure=replace(m.structure,energy=.15,grid=replace(m.structure.grid,period=period)))
        f=engine.render(m,c,at)
        frames.append(f)
        assert f.breakdown_calm and f.show_masks==() and f.show_step==0
        assert min(s.intensity for s in f.states[:4])>.04
    assert max(abs(a.states[j].intensity-b.states[j].intensity) for a,b in zip(frames,frames[1:]) for j in range(4))<.005
    assert len({tuple(round(v,2) for v in preview_rgb(f.states[0])) for f in frames})>=4


def test_calm_fades_are_identical_for_different_bpm_grids():
    engines=[LightingEngine(),LightingEngine()]
    for i in range(360):
        at=i/60
        outputs=[]
        for e,period in zip(engines,[.4,.66]):
            m=music(at,state="breakdown",tension=.2)
            m=replace(m,structure=replace(m.structure,energy=.15,grid=replace(m.structure.grid,period=period)))
            outputs.append(e.render(m,C,at))
        assert [s.intensity for s in outputs[0].states[:4]]==pytest.approx([s.intensity for s in outputs[1].states[:4]])


def test_calm_to_tense_blends_without_flapping_and_build_drop_take_priority():
    engine=LightingEngine()
    for i in range(120):
        at=i/60
        f=engine.render(music(at,state="breakdown",tension=.2),C,at)
    assert f.breakdown_calm
    blends=[]
    for i in range(120,300):
        at=i/60
        f=engine.render(music(at,state="breakdown",tension=.8),C,at)
        blends.append(f.breakdown_blend)
    assert all(a>=b for a,b in zip(blends,blends[1:])) and blends[-1]<.02
    for at,state in [(5,"buildup"),(5.1,"drop")]:
        f=engine.render(music(at,state=state,tension=.9),C,at)
        assert not f.breakdown_calm and f.breakdown_blend==0 and f.status==state
        assert max(s.intensity for s in f.states[:4])>.65


@pytest.mark.parametrize("override",["blackout","manual","disabled","stale"])
def test_calm_and_movers_do_not_bypass_overrides(override):
    c,m=C,music(.1,state="breakdown",tension=.2)
    if override=="blackout":c=replace(c,blackout=True)
    if override=="manual":c=replace(c,manual=True)
    if override=="disabled":c=replace(c,armed=False)
    if override=="stale":m=replace(m,audio_fresh=False)
    f=LightingEngine().render(m,c,.1)
    assert not f.breakdown_calm and f.mover_rhythm==""
    if override!="manual":assert all(s.intensity==s.white==0 for s in f.states)


def test_v11_preferences_migrate_and_new_styles_round_trip(tmp_path):
    old=validate(dict(version=11,light_phrase_pattern="sparks",light_phrase_variation="texture",
        light_mover_pattern="unknown",light_breakdown_style="unknown"))
    assert old.version == 13 and old.light_mover_pattern==old.light_breakdown_style=="auto"
    assert old.light_phrase_pattern=="sparks" and old.light_phrase_variation=="texture"
    store=SettingsStore(tmp_path/"styles.json")
    chosen=replace(old,light_mover_pattern="offbeat",light_breakdown_style="glow")
    store.save(chosen)
    assert store.load()==chosen


@pytest.mark.parametrize("field",["light_mover_pattern","light_breakdown_style"])
def test_invalid_styles_are_rejected(field):
    with pytest.raises(ValueError):LightConfig(**{field:"bad"})
