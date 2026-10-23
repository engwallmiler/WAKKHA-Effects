"""Regressões dos relatos de groove estacionado e sincronismo imperceptível."""
from dataclasses import replace
import math
import pytest
from beatlight.lighting.config import LightConfig, LightingControls
from beatlight.lighting.engine import LightingEngine
from beatlight.lighting.patterns import MOTIFS, RHYTHMS, FAMILIES, PatternPicker
from beatlight.lighting.show import ShowSequencer
from beatlight.configuration.store import Settings, validate
from test_rhythmic_show import music, seq

CFG=LightConfig(light_effect="phrase_show",light_transition_ms=0)
CONTROL=LightingControls(CFG,armed=True)


@pytest.mark.parametrize("feature,values",[
    ("density",(.2,.5)),("occupancy",(.2,.5)),("brightness",(.2,.45)),
    ("bass_level",(.25,.65)),("bass_activity",(.1,.4)),("onset_rate",(2,5)),
    ("density",(.7,.35)),("bass_level",(.75,.35)),
])
def test_significant_audio_change_switches_spatial_and_temporal_family_only_at_next_eight(feature,values):
    engine=LightingEngine()
    pending=False
    first=last=None
    for i in range(481):
        at=i/60
        m=music(at)
        m=replace(m,texture=replace(m.texture,**{feature:values[1] if at>=1.1 else values[0]}))
        frame=engine.render(m,CONTROL,at)
        first=first or frame
        pending |= frame.phrase_pending
        if at<4:assert frame.phrase_pattern==first.phrase_pattern
        elif last is None:last=frame
    assert pending and last.phrase_step==1
    assert FAMILIES[last.phrase_pattern]!=FAMILIES[first.phrase_pattern]
    assert last.show_masks!=first.show_masks
    assert frame.phrase_pattern==last.phrase_pattern and frame.show_fills==1
    assert frame.phrase_change_reason


def test_repetitive_beat_pulses_do_not_keep_changing_the_groove():
    engine=LightingEngine()
    patterns=set()
    for i in range(1441):
        at=i/60
        m=music(at)
        wave=(1+math.sin(4*math.pi*at))/2
        m=replace(m,texture=replace(m.texture,bass_level=.2+.7*wave,
            bass_activity=.1+.25*wave,brightness=.2+.15*wave))
        frame=engine.render(m,CONTROL,at)
        patterns.add(frame.phrase_pattern)
    assert len(patterns)==1 and frame.show_fills==0


def test_gradual_new_layer_is_compared_with_prior_context_not_absorbed_forever():
    engine=LightingEngine()
    pending=False
    for i in range(721):
        at=i/60
        density=.2+min(.3,max(0,at-2)*.04)
        frame=engine.render(music(at,density=density),CONTROL,at)
        pending |= frame.phrase_pending
    assert pending and frame.show_fills>=1


def test_dense_groove_starts_with_sequence_instead_of_alternating_pairs():
    frame=LightingEngine().render(music(0,density=.9),CONTROL,0)
    assert frame.phrase_pattern=="double"
    assert set(frame.show_masks)-{0,5,10,15}


def test_sensitivity_changes_threshold_and_round_trips():
    def changed(sensitivity):
        engine=LightingEngine()
        c=replace(CONTROL,config=replace(CFG,light_change_sensitivity=sensitivity))
        for i in range(481):
            at=i/60
            frame=engine.render(music(at,density=.28 if at>=1.1 else .2),c,at)
        return frame.show_fills
    assert changed(.5)==0 and changed(2)==1
    assert validate(dict(version=10,light_change_sensitivity="unknown-before-v11")).light_change_sensitivity==1
    assert validate(dict(version=11,light_change_sensitivity=1.5)).light_change_sensitivity==1.5


@pytest.mark.parametrize("value",[.49,2.01,math.nan,True])
def test_bad_sensitivity_is_rejected(value):
    with pytest.raises(ValueError):LightConfig(light_change_sensitivity=value)


def test_pattern_picker_has_variety_without_repeating_recent_patterns_or_same_family():
    picker=PatternPicker()
    current="chase"
    history=[current]
    for _ in range(32):
        chosen=picker.choose(current)
        assert chosen not in history[-3:] and FAMILIES[chosen]!=FAMILIES[current]
        current=chosen
        history.append(current)
    assert len(set(history))>=10


@pytest.mark.parametrize("pattern",list(RHYTHMS))
def test_new_rhythms_repeat_their_actual_half_beat_outputs_over_eight(pattern):
    engine=LightingEngine()
    c=replace(CONTROL,config=replace(CFG,light_phrase_pattern=pattern,light_phrase_prepare="none"))
    frames=[engine.render(music(i*.25+.01),c,i*.25+.01) for i in range(32)]
    for a,b in zip(frames,frames[16:]):
        assert [s.intensity for s in a.states]==pytest.approx([s.intensity for s in b.states])
    assert len({tuple(round(s.intensity,2) for s in f.states[:4]) for f in frames[:16]})>=4


def test_sync_produces_a_visible_collective_accent_once_and_preserves_pattern():
    engine=LightingEngine()
    c=replace(CONTROL,config=replace(CFG,light_phrase_pattern="pairs"))
    engine.render(music(0),c,0)
    c=replace(c,phrase_sync_id=1,phrase_sync_at=.27)
    frame=engine.render(music(.28),c,.28)
    assert frame.phrase_sync_flash and frame.phrase_step==1
    assert min(s.intensity for s in frame.states[:4])>.7
    assert all(s.white==1 for s in frame.states[:4])
    later=engine.render(music(.6),c,.6)
    assert not later.phrase_sync_flash and later.phrase_pattern=="pairs"
    assert later.phrase_sync_id==1 and later.phrase_synced


@pytest.mark.parametrize("state",["buildup","drop"])
def test_sync_of_structural_scene_aligns_actual_par_pattern_without_changing_drop_count(state):
    engine=LightingEngine()
    c=replace(CONTROL,phrase_sync_id=1,phrase_sync_at=.27)
    m=music(.28,state=state,drop_kicks=5,tension=.9)
    frame=engine.render(m,c,.28)
    assert frame.show_step==frame.phrase_step==1 and frame.phrase_synced
    assert not frame.phrase_sync_flash and not frame.phrase_preparation
    assert m.structure.drop_kicks==5
    assert frame.states[-2].pan+frame.states[-1].pan==pytest.approx(1)


def test_build_and_drop_variants_remain_stable_within_cycle_and_vary_across_entries():
    sequence=ShowSequencer()
    names=[]
    at=0
    for _ in range(8):
        for state in ("groove","buildup","groove","drop"):
            outputs=[]
            for j in range(20):
                m=music(at,state=state,tension=.9,drop_kicks=1)
                outputs.append(seq(sequence,m,at))
                at+=.01
            if state=="drop":
                assert len({f.rhythm for f in outputs})==1
                names.append(outputs[-1].rhythm)
                assert all(min(f.levels)>=.1 for f in outputs)
    assert len(set(names))>=3


@pytest.mark.parametrize("case",["blackout","manual","disabled","silence","stale"])
def test_sync_accent_cannot_bypass_operational_priorities(case):
    c=replace(CONTROL,phrase_sync_id=1,phrase_sync_at=.1)
    m=music(.1)
    if case=="blackout":c=replace(c,blackout=True)
    if case=="manual":c=replace(c,manual=True)
    if case=="disabled":c=replace(c,armed=False)
    if case=="silence":m=music(.1,state="silence")
    if case=="stale":m=replace(m,audio_fresh=False)
    f=LightingEngine().render(m,c,.1)
    assert not f.phrase_sync_flash
    if case!="manual":
        assert all(s.intensity==s.white==0 for s in f.states)
    else:
        assert f.status=="manual"


def test_structural_preview_matches_sparse_breakdown_hits():
    frame=LightingEngine().render(music(.7,state="breakdown",tension=.8),CONTROL,.7)
    assert frame.show_masks==(9,0,0,0,6,0,0,0)*2
    assert frame.show_rhythm=="Tensão espaçada"
    assert frame.show_phase==pytest.approx(.4)


def test_sync_in_fixed_color_mode_keeps_chosen_palette():
    from beatlight.lighting.config import PALETTES
    from beatlight.lighting.rgbw import preview_rgb
    c=replace(CONTROL,config=replace(CFG,light_color_mode="fixed",light_palette="red_blue"),
        phrase_sync_id=1,phrase_sync_at=.1)
    f=LightingEngine().render(music(.1),c,.1)
    assert f.phrase_sync_flash and min(s.intensity for s in f.states[:4])>.7
    assert all(any(preview_rgb(s)==pytest.approx(color) for color in PALETTES["red_blue"]) for s in f.states[:4])
