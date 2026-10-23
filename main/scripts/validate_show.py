"""QA em tempo real do Show rítmico, com palco aberto e fontes sintéticas."""
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
from beatlight.lighting.rgbw import preview_rgb
from beatlight.ui.window import MainWindow

root = Path(__file__).resolve().parents[1]
source = sys.argv[1] if len(sys.argv) > 1 else "structure_demo"
effect = sys.argv[2] if len(sys.argv) > 2 else "orchestrated_show"
assert effect in ("orchestrated_show", "rhythmic_show")
assert source in ("structure_demo", "texture_demo")
app = QApplication([])
if os.name == "nt":
    for name in ("segoeui.ttf", "segoeuib.ttf", "segoeuisl.ttf", "seguisym.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + name)
app.setStyle("Fusion")
app.setStyleSheet(STYLE)
window = MainWindow(SettingsStore(root / ".runtime" / "show-qa-preferences.json"),
    Settings(source=source, light_effect=effect, light_transition_ms=0))
window.show()
window._navigate(7)
end = monotonic() + 5
while (window.busy or not window.devices) and monotonic() < end:
    app.processEvents()
    sleep(.005)
patterns, transitions, captures = [], [], {}
geometries, errors, frame_ids = set(), set(), set()
levels = [[] for _ in range(4)]
colors = [set() for _ in range(4)]
contrasts, steps_without_kicks, confirmed_without_kicks = [], set(), set()
fills = 0
peak_novelty = peak_white = peak_processing = 0.0
last_pattern = last_state = None
white_peaks = [0.0] * 6
rgbw_valid = True
try:
    assert window.devices and not window.busy
    window.light_effect_combo.setCurrentIndex(window.light_effect_combo.findData(effect))
    assert window.light_runtime.controls().config.light_effect == effect
    window._start()
    window.stage_arm_button.click()
    end = monotonic() + (26 if source == "structure_demo" else 23)
    while monotonic() < end:
        app.processEvents()
        elapsed = window.runtime.status().elapsed
        audio, visual = window.runtime.snapshot(), window.light_runtime.snapshot()
        if audio and audio.structure and visual.show_pattern:
            if elapsed > 1:
                geometries.add(window.stage_view.geometry().getRect())
            if visual.frame_id not in frame_ids:
                frame_ids.add(visual.frame_id)
                for i, par in enumerate(visual.states[:4]):
                    levels[i].append(par.intensity)
                    colors[i].add(tuple(round(c, 3) for c in preview_rgb(par)))
                if visual.show_step:
                    contrasts.append(max(s.intensity for s in visual.states[:4]) - min(s.intensity for s in visual.states[:4]))
            if audio.structure.state != last_state:
                last_state = audio.structure.state
                transitions.append(dict(elapsed=round(elapsed, 3), state=last_state))
            if visual.show_pattern != last_pattern:
                last_pattern = visual.show_pattern
                patterns.append(dict(elapsed=round(elapsed, 3), pattern=last_pattern))
                print(patterns[-1], flush=True)
            if (source == "structure_demo" and 9 <= elapsed < 19) or (source == "texture_demo" and 7 <= elapsed < 17):
                steps_without_kicks.add(visual.show_step)
                confirmed_without_kicks.add(audio.kick_verification.confirmed_count)
            fills = max(fills, visual.show_fills)
            peak_novelty = max(peak_novelty, visual.show_novelty)
            peak_white = max(peak_white, min(min(preview_rgb(s)) for s in visual.states[:4]))
            for i, state in enumerate(visual.states):
                white_peaks[i] = max(white_peaks[i], state.white)
                rgbw_valid = rgbw_valid and all(0 <= c <= 1 for c in (*state.color, state.white))
            peak_processing = max(peak_processing, visual.processing_ms)
            for error in (audio.analysis_error, audio.kick_error, audio.beat_error, audio.structure_error,
                          audio.texture_error, audio.kick_verification_error, visual.error):
                if error:
                    errors.add(error)
            name = ("build" if visual.show_pattern == "buildup" and peak_white > .9 else
                    "drop" if visual.show_pattern == "drop" else
                    "fill" if visual.show_pattern == "fill" else
                    "groove" if visual.show_pattern not in ("acquiring", "breakdown", "buildup") and elapsed > 3 else None)
            if name and name not in captures and max(s.intensity for s in visual.states[:4]) > .45:
                window._tick()
                app.processEvents()
                captures[name] = window.grab().toImage()
        sleep(.005)
    status, audio, visual = window.runtime.status(), window.runtime.snapshot(), window.light_runtime.snapshot()
    report = dict(source=source, effect=effect, color_model="RGBW", white_peaks=white_peaks, rgbw_valid=rgbw_valid, physical_output=False, stage_open=True, duration=status.elapsed,
        status=asdict(status), continuity_errors=audio.continuity_errors, errors=sorted(errors),
        patterns=patterns, transitions=transitions, fills=fills, peak_novelty=peak_novelty,
        par_intensity_ranges=[dict(min=min(v), max=max(v)) for v in levels],
        par_distinct_colors=[len(c) for c in colors],
        frames_with_par_contrast_above_30_percent=sum(c > .3 for c in contrasts),
        clocked_frames=len(contrasts), steps_without_kicks=sorted(steps_without_kicks),
        confirmed_counts_without_kicks=sorted(confirmed_without_kicks),
        peak_white=peak_white, lighting_hz=visual.update_hz,
        peak_lighting_processing_ms=peak_processing, stage_geometries=sorted(geometries))
finally:
    window.close()
    end = monotonic() + 8
    while not window.closed_ready and monotonic() < end:
        app.processEvents()
        sleep(.005)
for name, capture in captures.items():
    capture.save(str(root / f"preview-rgbw-{source}-{name}.png"))
report["closed_cleanly"] = window.closed_ready and not window.light_runtime.running
report["final_intensities_zero"] = all(s.intensity == s.white == 0 and s.color == (0,0,0) for s in window.light_runtime.snapshot().states)
(root / "docs" / f"resultado-show-{source}-v0.16.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
assert report["closed_cleanly"] and report["final_intensities_zero"] and not errors
assert status.dropped_blocks == audio.continuity_errors == 0
assert len(geometries) == 1
assert rgbw_valid and all(v > .05 for v in white_peaks)
assert all(max(v) - min(v) > .4 for v in levels)
assert all(len(c) > 3 for c in colors)
assert report["frames_with_par_contrast_above_30_percent"] > len(contrasts) * .15
assert steps_without_kicks == set(range(1, 9))
assert len(confirmed_without_kicks) == 1
if source == "structure_demo":
    assert {p["pattern"] for p in patterns} >= {"chase", "breakdown", "buildup", "drop"}
    assert peak_white > .9
else:
    assert fills >= 1
