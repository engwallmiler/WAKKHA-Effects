"""Sessão sintética em tempo real com palco aberto, capturas e relatório de QA."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from dataclasses import asdict
import json
from pathlib import Path
import sys
from time import monotonic, sleep
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from beatlight.configuration.store import Settings, SettingsStore
from beatlight.ui.theme import STYLE
from beatlight.ui.window import MainWindow

root = Path(__file__).resolve().parents[1]
app = QApplication([])
if os.name == "nt":
    for name in ("segoeui.ttf", "segoeuib.ttf", "segoeuisl.ttf", "seguisym.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + name)
app.setStyle("Fusion")
app.setStyleSheet(STYLE)
window = MainWindow(SettingsStore(root / ".runtime" / "stage-qa-preferences.json"),
    Settings(source="structure_demo", light_effect="musical", light_transition_ms=0))
window.show()
window._navigate(7)
end = monotonic() + 5
while (window.busy or not window.devices) and monotonic() < end:
    app.processEvents()
    sleep(0.005)
transitions, counts, images, errors = [], [], [], []
captures = {}
geometries = set()
grid_prediction_observed = False
pause_phrases = set()
pause_confirmed = set()
color_profiles = set()
profile_peak = dict(movement_hz=0.0, white_mix=0.0, pre_drop_intensity=0.0)
try:
    assert window.devices and not window.busy
    window._start()
    window.light_arm_check.setChecked(True)
    end = monotonic() + 26
    last_state, last_count = None, 0
    while monotonic() < end:
        app.processEvents()
        snapshot = window.runtime.snapshot()
        if snapshot and snapshot.structure:
            music = snapshot.structure
            visual = window.light_runtime.snapshot()
            elapsed = window.runtime.status().elapsed
            if 9 <= elapsed < 19:
                pause_phrases.add(music.phrase_kick)
                pause_confirmed.add(window.runtime.snapshot().kick_verification.confirmed_count)
            color_profiles.add(visual.color_profile)
            if music.grid and music.grid.state == "predicting" and music.grid.forecast_30_at:
                grid_prediction_observed = True
            if window.runtime.status().elapsed > 0.5:
                geometries.add(window.stage_view.geometry().getRect())
            if music.state == "buildup":
                profile_peak["movement_hz"] = max(profile_peak["movement_hz"], visual.movement_hz)
                profile_peak["white_mix"] = max(profile_peak["white_mix"], visual.white_mix)
                profile_peak["pre_drop_intensity"] = max(profile_peak["pre_drop_intensity"], max(f.intensity for f in visual.states))
            if music.state != last_state:
                transitions.append(dict(elapsed=round(window.runtime.status().elapsed, 3), state=music.state))
                print(transitions[-1], flush=True)
                last_state = music.state
            if (music.state in ("breakdown", "buildup", "drop") and music.state not in images
                    and window.light_runtime.snapshot().status == music.state):
                if ((music.state != "buildup" or visual.white_mix > 0.85)
                        and (music.state != "drop" or music.drop_kicks >= 2)):
                    window._tick()
                    app.processEvents()
                    # Codificação PNG fica fora da sessão para não disputar o GIL com o DSP.
                    captures[music.state] = window.grab().toImage()
                    images.append(music.state)
            if music.state == "drop" and music.drop_kicks != last_count:
                counts.append(music.drop_kicks)
                last_count = music.drop_kicks
            for error in (snapshot.analysis_error, snapshot.kick_error, snapshot.beat_error, snapshot.structure_error, window.light_runtime.snapshot().error):
                if error and error not in errors:
                    errors.append(error)
        sleep(0.005)
    status, snapshot, light = window.runtime.status(), window.runtime.snapshot(), window.light_runtime.snapshot()
    report = dict(source="synthetic_structure_demo", physical_output=False, stage_open=True,
        status=asdict(status), continuity_errors=snapshot.continuity_errors,
        transitions=transitions, drop_kicks=counts, lighting_hz=light.update_hz,
        lighting_processing_ms=light.processing_ms, errors=errors,
        stage_geometries=sorted(geometries), build_up_profile_peak=profile_peak,
        grid_prediction_observed=grid_prediction_observed, color_profiles=sorted(color_profiles),
        phrase_steps_without_kicks=sorted(pause_phrases), confirmed_counts_during_pause=sorted(pause_confirmed))
finally:
    window.close()
    end = monotonic() + 8
    while not window.closed_ready and monotonic() < end:
        app.processEvents()
        sleep(0.005)
for name, capture in captures.items():
    capture.save(str(root / ("preview-" + name + ".png")))
report["closed_cleanly"] = window.closed_ready and not window.light_runtime.running
report["final_intensities_zero"] = all(s.intensity == 0 for s in window.light_runtime.snapshot().states)
(root / "docs" / "resultado-palco-v0.16.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
assert report["closed_cleanly"] and not errors
assert [t["state"] for t in transitions] == ["warming", "groove", "breakdown", "buildup", "drop", "groove"]
assert counts == list(range(1, 9))
assert status.dropped_blocks == 0 and snapshot.continuity_errors == 0

assert len(geometries) == 1, sorted(geometries)
assert profile_peak["white_mix"] > 0.85

assert grid_prediction_observed
assert any("build-up" in name for name in color_profiles) and any("drop" in name for name in color_profiles)

assert pause_phrases == set(range(1, 9))
assert len(pause_confirmed) == 1
assert next(t["elapsed"] for t in transitions if t["state"] == "groove") < 2.5
