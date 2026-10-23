"""QA em tempo real: sincronização, preparação, repetição, textura e oito kicks."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from dataclasses import asdict
import json
from pathlib import Path
import sys
from time import monotonic,sleep
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE
from beatlight.lighting.patterns import MOTIFS
from beatlight.lighting.rgbw import preview_rgb
root=Path(__file__).resolve().parents[1]
source=sys.argv[1] if len(sys.argv)>1 else "structure_demo"
assert source in ("structure_demo","texture_demo","synthetic")
variation=sys.argv[2] if len(sys.argv)>2 else Settings().light_phrase_variation
assert variation in ("texture","cycle","two_cycles")
app=QApplication([])
if os.name=="nt":
    for name in ("segoeui.ttf","segoeuib.ttf","segoeuisl.ttf","seguisym.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/"+name)
app.setStyle("Fusion");app.setStyleSheet(STYLE)
window=MainWindow(SettingsStore(root/".runtime"/"phrase-qa-preferences.json"),
    Settings(source=source,light_effect="orchestrated_show",light_transition_ms=0,light_phrase_variation=variation))
window.show();window._navigate(7)
end=monotonic()+5
while (window.busy or not window.devices) and monotonic()<end:
    app.processEvents();sleep(.005)
geometry=set();errors=set();patterns=[];captures={};drop={};seen=set()
mover_frames=0;cycle_patterns={};sync_cycle_patterns={}
par_groups=set();groove_programs=set();sync_flash_frames=0;sync_minimum=1.0;change_reasons=set();structural_rhythms=set()
preparation={"fade":[],"blackout":[]};pause_steps=set();pause_counts=set()
sync=None;last_pattern=None;last_gain=1.0;resumed=0;pending_seen=False
mover_styles=set();mover_colors=set();mover_levels=[];calm_frames=0;calm_deltas=[];previous_calm=None;rejected_returns=0
try:
    assert window.devices and not window.busy
    window.stage_show_button.click();assert window.light_effect_combo.currentData()=="phrase_show"
    window._start();window.stage_arm_button.click()
    end=monotonic()+(26 if source=="structure_demo" else 23 if source=="texture_demo" else 21)
    while monotonic()<end:
        app.processEvents()
        elapsed=window.runtime.status().elapsed
        if sync is None and elapsed>3.05 and window.stage_sync_button.isEnabled():
            original=window.runtime.snapshot().structure.grid.phrase_origin
            window.light_effect_combo.setCurrentIndex(window.light_effect_combo.findData("orchestrated_show"))
            window._tick();assert window.stage_sync_button.isEnabled()
            window.stage_sync_button.click()
            assert window.light_effect_combo.currentData()=="phrase_show"
            sync=dict(elapsed=elapsed,at=window.light_runtime.controls().phrase_sync_at,
                      command=window.light_runtime.controls().phrase_sync_id,original_grid_origin=original)
        if source=="texture_demo" and elapsed>8 and window.light_prepare_combo.currentData()!="blackout":
            window.light_prepare_combo.setCurrentIndex(window.light_prepare_combo.findData("blackout"))
        audio=window.runtime.snapshot();light=window.light_runtime.snapshot()
        if audio and audio.structure and light.frame_id not in seen:
            seen.add(light.frame_id)
            a,b=light.states[-2:]
            assert abs(a.intensity-b.intensity)<1e-9 and a.color==b.color and a.white==b.white
            assert abs(a.pan+b.pan-1)<1e-9 and a.tilt==b.tilt
            mover_frames+=1
            rejected_returns=max(rejected_returns,audio.structure.rejected_returns)
            if light.mover_rhythm:
                mover_styles.add(light.mover_rhythm)
                mover_colors.add(tuple(round(v,1) for v in preview_rgb(a)))
                mover_levels.append(a.intensity)
            if light.breakdown_calm:
                calm_frames+=1
                if source=="structure_demo" and 9.5<=elapsed<11.5 and light.breakdown_blend>.99:
                    levels=tuple(s.intensity for s in light.states[:4])
                    if previous_calm:
                        calm_deltas.append(max(abs(x-y) for x,y in zip(levels,previous_calm)))
                    previous_calm=levels
            if light.phrase_sync_flash:
                sync_flash_frames+=1
                sync_minimum=min(sync_minimum,min(s.intensity for s in light.states[:4]))
            if light.phrase_change_reason:change_reasons.add(light.phrase_change_reason)
            if light.status=="active" and light.phrase_step:
                groove_programs.add(tuple(light.show_masks))
                par_groups.add(sum(1<<i for i,s in enumerate(light.states[:4]) if s.intensity>.2))
            if light.status in ("buildup","drop"):structural_rhythms.add(light.show_rhythm)
            if light.phrase_step:
                cycle_patterns.setdefault(light.phrase_cycle, light.phrase_pattern)
                if sync and light.phrase_synced:
                    sync_cycle_patterns.setdefault(light.phrase_cycle,light.phrase_pattern)
            if elapsed>1:geometry.add(window.stage_view.geometry().getRect())
            if light.phrase_pending:pending_seen=True
            if light.show_pattern and light.show_pattern!=last_pattern:
                last_pattern=light.show_pattern
                patterns.append(dict(elapsed=round(elapsed,3),pattern=last_pattern,cycle=light.phrase_cycle,step=light.phrase_step))
            if sync and light.phrase_sync_id==sync["command"] and light.phrase_synced and "observed_step" not in sync:
                sync.update(observed_step=light.phrase_step,observed_phase=light.phrase_phase,
                    grid_origin_unchanged=audio.structure.grid.phrase_origin==sync["original_grid_origin"])
            mode=window.light_prepare_combo.currentData()
            if light.phrase_preparation:
                preparation[mode].append(light.phrase_gain)
                if mode=="blackout":
                    assert all(s.intensity==s.white==0 and s.color==(0,0,0) for s in light.states)
                name="preparation-"+mode
            elif last_gain<.5 and light.phrase_step==1:
                resumed+=1;name="impact"
            elif audio.structure.state=="drop" and audio.structure.drop_kicks==8 and max(s.intensity for s in light.states[:4])>.7:
                name="drop-eight"
            elif light.breakdown_calm and 9.5<=elapsed<11.5:
                name="calm"
            elif light.mover_rhythm and 5<=elapsed<7 and min(a.intensity,b.intensity)>.45:
                name="movers"
            elif light.phrase_sync_flash:
                name="sync"
            elif light.show_fills>0 and light.phrase_step==1 and light.status=="active":name="variation"
            else:name=None
            if name and name not in captures:
                window._tick();app.processEvents();window.stage_view.set_snapshot(light);window.stage_pattern_view.set_snapshot(light);captures[name]=window.grab().toImage()
            last_gain=light.phrase_gain
            if light.status=="drop" and audio.structure.state=="drop":
                count=audio.structure.drop_kicks
                row=drop.setdefault(count,dict(first=elapsed,last=elapsed,peak=0.0,frames=0))
                row.update(last=elapsed,peak=max(row["peak"],max(s.intensity for s in light.states[:4])),frames=row["frames"]+1)
            if (source=="structure_demo" and 9<=elapsed<19) or (source=="texture_demo" and 7.5<=elapsed<17):
                pause_steps.add(light.phrase_step);pause_counts.add(audio.kick_verification.confirmed_count)
            for error in (audio.analysis_error,audio.kick_error,audio.beat_error,audio.structure_error,
                          audio.texture_error,audio.kick_verification_error,light.error):
                if error:errors.add(error)
        sleep(.005)
    status=window.runtime.status();audio=window.runtime.snapshot();light=window.light_runtime.snapshot()
    report=dict(source=source,variation=variation,physical_output=False,effect="phrase_show",status=asdict(status),
        continuity_errors=audio.continuity_errors,errors=sorted(errors),stage_geometries=sorted(geometry),
        patterns=patterns,sync=sync,pending_texture_change_observed=pending_seen,
        coordinated_mover_frames=mover_frames,cycles_after_sync=sync_cycle_patterns,
        mover_rhythms=sorted(mover_styles),mover_color_count=len(mover_colors),
        mover_level_range=[min(mover_levels),max(mover_levels)] if mover_levels else [],
        calm_frames=calm_frames,calm_max_delta=max(calm_deltas) if calm_deltas else None,
        rejected_returns=rejected_returns,
        par_groups=sorted(par_groups),groove_programs=len(groove_programs),sync_flash_frames=sync_flash_frames,
        sync_minimum_par_intensity=sync_minimum,change_reasons=sorted(change_reasons),structural_rhythms=sorted(structural_rhythms),
        preparations={k:dict(frames=len(v),minimum_gain=min(v) if v else None) for k,v in preparation.items()},
        resumed_after_preparation=resumed,drop=drop,pause_steps=sorted(pause_steps),pause_confirmed=sorted(pause_counts),
        lighting_hz=light.update_hz,lighting_processing_ms=light.processing_ms)
finally:
    window.close();end=monotonic()+8
    while not window.closed_ready and monotonic()<end:app.processEvents();sleep(.005)
for name,capture in captures.items():capture.save(str(root/f"preview-cycles-{source}-{name}.png"))
report["closed_cleanly"]=window.closed_ready and not window.light_runtime.running
report["final_zero"]=all(s.intensity==s.white==0 and s.color==(0,0,0) for s in window.light_runtime.snapshot().states)
(root/"docs"/f"resultado-ciclos-{source}-v0.18.0-{variation}.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
assert report["closed_cleanly"] and report["final_zero"] and not errors
assert status.dropped_blocks==audio.continuity_errors==0
assert len(geometry)==1
assert sync["observed_step"]==1 and sync["grid_origin_unchanged"]
assert preparation["fade"] and resumed>=1
assert sync_flash_frames>=4 and sync_minimum>.7
if source!="synthetic":assert pause_steps==set(range(1,9)) and len(pause_counts)==1
if source=="structure_demo":
    assert calm_frames>60 and calm_deltas and max(calm_deltas)<.025
    assert set(drop)==set(range(1,9))
    assert all(row["last"]-row["first"]>.35 and row["peak"]>.7 for row in drop.values())
elif source=="texture_demo":
    assert preparation["blackout"] and pending_seen
    assert len({p["pattern"] for p in patterns if p["pattern"] in MOTIFS})>=2
    assert len(groove_programs)>=2 and len(par_groups)>=6

if source=="synthetic":
    if variation=="texture":
        assert len(sync_cycle_patterns)>=5 and len(set(sync_cycle_patterns.values()))==1
        assert not pending_seen
    elif variation=="two_cycles":
        assert sync_cycle_patterns[1]==sync_cycle_patterns[2]
        assert sync_cycle_patterns[3]==sync_cycle_patterns[4]!=sync_cycle_patterns[1]
        assert sync_cycle_patterns[5]!=sync_cycle_patterns[3]
    else:
        assert all(sync_cycle_patterns[i]!=sync_cycle_patterns[i+1] for i in range(1,5))
assert mover_frames>900

assert len(mover_colors)>=8 and max(mover_levels)-min(mover_levels)>.2
