"""QA Qt em tempo real: bassline sem kick e cenas guiadas por textura, sem saída física."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from dataclasses import asdict
import json
from pathlib import Path
import sys
from time import monotonic,sleep
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.ui.theme import STYLE
from beatlight.ui.window import MainWindow

root=Path(__file__).resolve().parents[1]
app=QApplication([])
if os.name=="nt":
    for name in ("segoeui.ttf","segoeuib.ttf","segoeuisl.ttf","seguisym.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/"+name)
app.setStyle("Fusion")
app.setStyleSheet(STYLE)
window=MainWindow(SettingsStore(root/".runtime"/"texture-qa-preferences.json"),Settings(source="texture_demo",light_effect="musical",light_transition_ms=0))
window.show()
window._navigate(7)
end=monotonic()+5
while (window.busy or not window.devices) and monotonic()<end:
    app.processEvents();sleep(0.005)
captures={}
levels={"sparse":[],"dense":[]}
geometry=set()
errors=set()
confirmed_without_kick=set()
bass_lit=[]
audio_origin=None
try:
    assert window.devices and not window.busy
    window._start()
    window.light_arm_check.setChecked(True)
    end=monotonic()+23
    selected="musical"
    while monotonic()<end:
        app.processEvents()
        elapsed=window.runtime.status().elapsed
        effect="bass_flow" if 7<=elapsed<12 else "density_wash" if 12<=elapsed<18 else "musical"
        if effect!=selected:
            window.light_effect_combo.setCurrentIndex(window.light_effect_combo.findData(effect))
            selected=effect
        snapshot=window.runtime.snapshot()
        visual=window.light_runtime.snapshot()
        if snapshot and snapshot.texture:
            texture=snapshot.texture
            if audio_origin is None:
                audio_origin=snapshot.acquired_at-snapshot.sequence*window.runtime.status().stream_format.block_size/48000
            if elapsed>1:
                geometry.add(window.stage_view.geometry().getRect())
            if 8<=elapsed<11:
                levels["sparse"].append(texture.density)
                bass_lit.append(max(f.intensity for f in visual.states))
            if 14<=elapsed<17:
                levels["dense"].append(texture.density)
            if 7<=elapsed<17 and snapshot.kick_verification:
                confirmed_without_kick.update(e.occurred_at for e in snapshot.kick_verification.confirmed_events if e.occurred_at>=audio_origin+6.3)
            for error in (snapshot.analysis_error,snapshot.kick_error,snapshot.beat_error,snapshot.structure_error,snapshot.texture_error,snapshot.kick_verification_error,visual.error):
                if error: errors.add(error)
            name="baixo" if 9<elapsed<11 else "densidade" if 15<elapsed<17 else None
            if name and name not in captures and visual.effect==effect and max(f.intensity for f in visual.states)>0.2:
                window._tick();app.processEvents()
                captures[name]=window.grab().toImage()
        sleep(0.005)
    status=window.runtime.status()
    snapshot=window.runtime.snapshot()
    report=dict(source="synthetic_texture_demo",physical_output=False,status=asdict(status),continuity_errors=snapshot.continuity_errors,
        sparse_density=sum(levels["sparse"])/len(levels["sparse"]),dense_density=sum(levels["dense"])/len(levels["dense"]),
        minimum_bass_scene_intensity=min(bass_lit),mean_bass_scene_intensity=sum(bass_lit)/len(bass_lit),peak_bass_scene_intensity=max(bass_lit),confirmed_in_bass_only_section=len(confirmed_without_kick),
        verification=asdict(snapshot.kick_verification),stage_geometries=sorted(geometry),errors=sorted(errors))
finally:
    window.close()
    end=monotonic()+8
    while not window.closed_ready and monotonic()<end:
        app.processEvents();sleep(0.005)
for name,capture in captures.items():capture.save(str(root/("preview-"+name+".png")))
report["closed_cleanly"]=window.closed_ready and not window.light_runtime.running
report["final_intensities_zero"]=all(s.intensity==0 for s in window.light_runtime.snapshot().states)
(root/"docs"/"resultado-textura-v0.16.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
assert not errors and report["closed_cleanly"] and report["final_intensities_zero"]
assert status.dropped_blocks==snapshot.continuity_errors==0
assert len(geometry)==1
assert report["dense_density"]>report["sparse_density"]+0.1
assert report["mean_bass_scene_intensity"]>0.1
assert report["peak_bass_scene_intensity"]>0.25
assert set(captures)=={"baixo","densidade"}
assert report["confirmed_in_bass_only_section"]==0
