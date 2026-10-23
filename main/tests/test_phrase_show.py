from dataclasses import replace
import math
import pytest
from beatlight.contracts import LightingInput
from beatlight.configuration.store import Settings,SettingsStore,validate
from beatlight.lighting.config import LightConfig,LightingControls
from beatlight.lighting.engine import LightingEngine
from beatlight.lighting.phrase import MOTIFS
from test_rhythmic_show import music

CFG=LightConfig(light_effect="phrase_show",light_transition_ms=0,light_phrase_variation="texture")
CONTROLS=LightingControls(CFG,armed=True)


@pytest.mark.parametrize("pattern",list(MOTIFS))
def test_each_motif_repeats_eight_tempo_levels_and_colors_while_texture_is_stable(pattern):
    c=replace(CONTROLS,config=replace(CFG,light_phrase_pattern=pattern,light_phrase_prepare="none"))
    engine=LightingEngine()
    f=[engine.render(music(i*.5+.01),c,i*.5+.01) for i in range(32)]
    assert {v.show_pattern for v in f}=={pattern}
    for i in range(24):
        assert [s.intensity for s in f[i].states]==pytest.approx([s.intensity for s in f[i+8].states])
        assert [s.color for s in f[i].states]==[s.color for s in f[i+8].states]
    if pattern=="unison": assert min(s.intensity for s in f[0].states)>.7
    if pattern=="chase": assert len({max(range(4),key=lambda j:x.states[j].intensity) for x in f[:4]})==4


def test_auto_pattern_waits_for_next_full_cycle_after_sustained_new_layer():
    engine=LightingEngine()
    f=[]
    for i in range(481):
        at=i/60
        f.append(engine.render(music(at,density=.9 if at>=1 else .2,onset=8 if at>=1 else 2),CONTROLS,at))
    assert {x.show_pattern for x in f[:240]}=={"chase"}
    assert any(x.phrase_pending for x in f[70:240])
    assert f[240].show_pattern!="chase" and f[240].phrase_step==1
    assert {x.show_pattern for x in f[240:]}=={f[240].show_pattern}
    assert f[-1].show_fills==1


def test_an_isolated_attack_or_static_loop_does_not_keep_rotating_patterns():
    engine=LightingEngine()
    f=[]
    for i in range(721):
        at=i/60
        transient=60<=i<=61
        f.append(engine.render(music(at,density=.95 if transient else .2,onset=10 if transient else 2),CONTROLS,at))
    assert {x.show_pattern for x in f}=={"chase"}
    assert not any(x.phrase_pending for x in f)


@pytest.mark.parametrize("mode",["fade","blackout","none"])
def test_global_preparation_is_short_and_releases_on_first_beat(mode):
    engine=LightingEngine()
    c=replace(CONTROLS,config=replace(CFG,light_phrase_prepare=mode,light_phrase_pattern="unison"))
    start=engine.render(music(3.8),c,3.8)
    middle=engine.render(music(3.9),c,3.9)
    end=engine.render(music(3.98),c,3.98)
    impact=engine.render(music(4),c,4)
    assert not start.phrase_preparation and not impact.phrase_preparation
    assert impact.phrase_step==1 and impact.phrase_cycle==2
    assert min(s.intensity for s in impact.states)>.7
    assert not end.blackout
    if mode=="fade":
        assert 0<end.phrase_gain<middle.phrase_gain<1
        assert max(s.intensity for s in end.states)<.04
    elif mode=="blackout":
        assert middle.phrase_gain==end.phrase_gain==0
        assert all(s.intensity==s.white==0 and s.color==(0,0,0) for s in end.states)
    else:
        assert start.phrase_gain==middle.phrase_gain==end.phrase_gain==1


def test_preparation_does_not_override_manual_blackout_or_drop():
    for control in (replace(CONTROLS,manual=True),replace(CONTROLS,blackout=True)):
        f=LightingEngine().render(music(3.98),control,3.98)
        assert not f.phrase_preparation
        if control.manual: assert all(s.intensity==pytest.approx(.56) for s in f.states)
        else: assert all(s.intensity==s.white==0 for s in f.states)
    f=LightingEngine().render(music(3.98,state="drop",drop_kicks=8),CONTROLS,3.98)
    assert f.status=="drop" and not f.phrase_preparation and f.phrase_gain==1


def test_sync_uses_click_time_preserves_bpm_and_continues_without_kicks():
    engine=LightingEngine()
    for i in range(83): engine.render(music(i/60),CONTROLS,i/60)
    at=1.383
    m=music(at)
    c=replace(CONTROLS,phrase_sync_id=1,phrase_sync_at=1.37)
    f=engine.render(m,c,at)
    assert f.phrase_step==f.phrase_cycle==1 and f.phrase_synced
    assert f.phrase_phase==pytest.approx((at-1.37)/.5)
    assert m.structure.grid.period==.5 and m.structure.grid.phrase_origin==0 and not m.confirmed_kicks
    for i in range(1,241):
        at=1.383+i/60
        f=engine.render(music(at),c,at)
    assert f.phrase_cycle==2 and f.phrase_step==1
    assert f.phrase_phase==pytest.approx(.026)


def test_sync_does_not_change_existing_drop_count_or_wait_for_next_worker_frame():
    at=10.137
    m=music(at,state="drop",drop_kicks=5)
    c=replace(CONTROLS,phrase_sync_id=1,phrase_sync_at=10.12)
    f=LightingEngine().render(m,c,at)
    assert f.status=="drop" and f.phrase_synced and f.phrase_step==1
    assert m.structure.drop_kicks==5


def test_sync_alignment_is_cleared_by_stop_and_grid_correction_without_replaying_old_click():
    engine=LightingEngine()
    c=replace(CONTROLS,phrase_sync_id=1,phrase_sync_at=.1)
    assert engine.render(music(.1),c,.1).phrase_synced
    stopped=engine.render(LightingInput(),c,.2)
    assert not stopped.phrase_synced and stopped.phrase_step==0
    assert not engine.render(music(.3),c,.3).phrase_synced
    c=replace(c,phrase_sync_id=2,phrase_sync_at=.4)
    assert engine.render(music(.4),c,.4).phrase_synced
    m=music(.5)
    m=replace(m,structure=replace(m.structure,grid=replace(m.structure.grid,revision=1)))
    assert not engine.render(m,c,.5).phrase_synced


def test_click_without_clock_is_not_saved_for_later_playback():
    engine=LightingEngine()
    c=replace(CONTROLS,phrase_sync_id=1,phrase_sync_at=.1)
    assert not engine.render(music(.1,grid=False),c,.1).phrase_synced
    assert not engine.render(music(.2),c,.2).phrase_synced


def test_new_preferences_migrate_and_round_trip_without_persisting_sync_command(tmp_path):
    old=validate(dict(version=8,light_effect="orchestrated_show",light_white_strength=.8,
        light_phrase_pattern="unknown-before-v9"))
    assert old.version == 13 and old.light_phrase_pattern=="auto" and old.light_white_strength==.8
    store=SettingsStore(tmp_path/"phrase.json")
    s=replace(old,light_effect="phrase_show",light_phrase_pattern="reverse",light_phrase_prepare="blackout",light_phrase_prepare_ms=180)
    store.save(s)
    assert store.load()==s and "phrase_sync_at" not in store.path.read_text()


@pytest.mark.parametrize("fields",[{"light_phrase_pattern":"bad"},{"light_phrase_prepare":"bad"},
    {"light_phrase_prepare_ms":math.nan},{"light_phrase_prepare_ms":301}])
def test_invalid_cycle_settings_are_rejected(fields):
    with pytest.raises(ValueError): LightConfig(**fields)


def test_new_layer_change_survives_build_overlay_until_return_to_groove():
    engine=LightingEngine()
    frames=[]
    for i in range(361):
        at=i/60
        state="buildup" if 2<=at<5 else "groove"
        frames.append(engine.render(music(at,state=state,density=.9 if at>=1 else .2,
            onset=8 if at>=1 else 2),CONTROLS,at))
    assert frames[90].phrase_pending
    assert frames[180].phrase_pending and frames[180].show_pattern=="buildup"
    assert not frames[240].phrase_pending and frames[240].show_pattern=="buildup"
    assert frames[300].show_pattern==frames[240].phrase_pattern!="chase" and frames[300].show_fills==1
    assert all(not f.phrase_preparation for f in frames[120:300])


def test_resynchronizing_preserves_the_newly_selected_motif():
    engine=LightingEngine()
    for i in range(289):
        at=i/60
        f=engine.render(music(at,density=.9 if at>=1 else .2,onset=8 if at>=1 else 2),CONTROLS,at)
    chosen=f.show_pattern
    assert chosen!="chase"
    c=replace(CONTROLS,phrase_sync_id=1,phrase_sync_at=4.9)
    f=engine.render(music(4.91,density=.9,onset=8),c,4.91)
    assert f.show_pattern==chosen and f.phrase_step==1 and f.phrase_synced
    c=replace(c,phrase_sync_id=2,phrase_sync_at=5.1)
    f=engine.render(music(5.11,density=.9,onset=8),c,5.11)
    assert f.show_pattern==chosen and f.phrase_step==1


@pytest.mark.parametrize("override",["blackout","manual"])
def test_temporary_override_keeps_manual_alignment_while_audio_continues(override):
    engine=LightingEngine()
    c=replace(CONTROLS,phrase_sync_id=1,phrase_sync_at=.1)
    assert engine.render(music(.1),c,.1).phrase_synced
    blocked=replace(c,**{override:True})
    for i in range(1,21):
        at=.1+i*.1
        f=engine.render(music(at),blocked,at)
        assert f.phrase_synced
        if override=="blackout":assert all(s.intensity==0 for s in f.states)
    f=engine.render(music(2.2),c,2.2)
    assert f.phrase_synced and f.phrase_step==5 and f.phrase_phase==pytest.approx(.2)


def test_click_newer_than_worker_timestamp_is_applied_on_next_frame():
    engine=LightingEngine()
    c=replace(CONTROLS,phrase_sync_id=1,phrase_sync_at=1.11)
    first=engine.render(music(1.1),c,1.1)
    assert not first.phrase_synced and first.phrase_sync_id==0
    next_frame=engine.render(music(1.12),c,1.12)
    assert next_frame.phrase_synced and next_frame.phrase_sync_id==1
    assert next_frame.phrase_step==1 and next_frame.phrase_phase==pytest.approx(.02)

@pytest.mark.parametrize("policy",["two_cycles","cycle","texture"])
def test_variation_policy_changes_only_on_eight_beat_boundaries(policy):
    engine=LightingEngine()
    controls=replace(CONTROLS,config=replace(CFG,light_phrase_variation=policy))
    patterns=[]
    for i in range(1440):
        at=i/60
        frame=engine.render(music(at),controls,at)
        if i%240==0: patterns.append(frame.phrase_pattern)
        assert frame.phrase_pattern==patterns[-1]
    if policy=="texture":
        assert len(set(patterns))==1
    elif policy=="two_cycles":
        assert patterns[0]==patterns[1] and patterns[2]==patterns[3] and patterns[4]==patterns[5]
        assert len(set(patterns))==3
    else:
        assert len(set(patterns))>=4
        assert all(a!=b for a,b in zip(patterns,patterns[1:]))


def test_new_layer_and_periodic_rotation_on_same_boundary_change_only_once():
    engine=LightingEngine()
    controls=replace(CONTROLS,config=replace(CFG,light_phrase_variation="cycle"))
    for i in range(241):
        at=i/60
        frame=engine.render(music(at,density=.9 if at>=1 else .2,onset=8 if at>=1 else 2),controls,at)
    assert frame.phrase_pattern!="chase" and frame.show_fills==1


def test_partial_acquisition_and_resync_do_not_shorten_two_full_repetitions():
    engine=LightingEngine()
    controls=replace(CONTROLS,config=replace(CFG,light_phrase_variation="two_cycles"))
    for i in range(60,721):
        at=i/60
        frame=engine.render(music(at),controls,at)
        if at<12:assert frame.phrase_pattern=="chase"
    chosen=frame.phrase_pattern
    assert chosen!="chase"
    controls=replace(controls,phrase_sync_id=1,phrase_sync_at=12.1)
    for i in range(727,1206):
        at=i/60
        frame=engine.render(music(at),controls,at)
        assert frame.phrase_pattern==chosen
    frame=engine.render(music(20.1),controls,20.1)
    assert frame.phrase_pattern!=chosen and frame.phrase_step==1


def test_switching_to_phrase_with_sync_has_immediate_impact_without_mode_fade():
    engine=LightingEngine()
    old=LightingControls(LightConfig(light_effect="orchestrated_show"),armed=True)
    engine.render(music(0),old,0)
    controls=replace(old,config=replace(old.config,light_effect="phrase_show",light_phrase_pattern="unison"),
        phrase_sync_id=1,phrase_sync_at=.1)
    frame=engine.render(music(.1),controls,.1)
    assert frame.phrase_synced and frame.phrase_step==1
    assert min(s.intensity for s in frame.states)>.7


def test_v9_migrates_variation_default_and_v10_preserves_policy():
    s=validate(dict(version=9,light_effect="phrase_show",light_phrase_pattern="chase",
        light_phrase_variation="unknown-before-v10"))
    assert s.version == 13 and s.light_phrase_variation=="texture" and s.light_phrase_pattern=="chase"
    assert validate(dict(version=10,light_phrase_variation="cycle")).light_phrase_variation=="cycle"
    with pytest.raises(ValueError):validate(dict(version=10,light_phrase_variation="bad"))

def test_resync_rebases_novelty_cooldown_to_new_visual_position():
    engine=LightingEngine()
    for i in range(301):
        at=i/60
        frame=engine.render(music(at,density=.9 if at>=1 else .2,onset=8 if at>=1 else 2),CONTROLS,at)
    chosen=frame.phrase_pattern
    assert chosen!="chase"
    controls=replace(CONTROLS,phrase_sync_id=1,phrase_sync_at=5.1)
    pending=False
    for i in range(306,547):
        at=i/60
        frame=engine.render(music(at,density=.9,onset=8,bass=.95 if at>=6 else .4),controls,at)
        pending |= frame.phrase_pending
    assert pending and frame.phrase_pattern!=chosen
