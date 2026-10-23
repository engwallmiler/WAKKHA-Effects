"""QA Qt: grade e efeitos seguem sem kick mesmo após a expiração do PLL."""
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
window = MainWindow(SettingsStore(root / ".runtime" / "grid-qa-preferences.json"),
    Settings(source="structure_demo", light_effect="beat_pulse", light_transition_ms=0))
window.show()
window._navigate(7)
end = monotonic() + 5
while (window.busy or not window.devices) and monotonic() < end:
    app.processEvents()
    sleep(0.005)
phrases, expected, confirmed, geometry, errors = set(), set(), set(), set(), set()
intensities, phases = [], []
capture = None
pll_expired = False
acquired = None
try:
    assert window.devices and not window.busy
    window._start()
    window.light_arm_check.setChecked(True)
    end = monotonic() + 16
    while monotonic() < end:
        app.processEvents()
        elapsed = window.runtime.status().elapsed
        page = 5 if 10 <= elapsed < 13 else 7
        if window.pages.currentIndex() != page:
            window._navigate(page)
        snapshot = window.runtime.snapshot()
        light = window.light_runtime.snapshot()
        if snapshot and snapshot.structure:
            structure = snapshot.structure
            grid = structure.grid
            if grid and grid.state in ("tracking", "predicting") and acquired is None:
                acquired = elapsed
            if elapsed > 1 and page == 7:
                geometry.add(window.stage_view.geometry().getRect())
            if 9 <= elapsed < 16 and grid:
                phrases.add(structure.phrase_kick)
                phases.append(grid.phase)
                intensities.append(max(s.intensity for s in light.states))
                audit = snapshot.kick_verification
                confirmed.add(audit.confirmed_count)
                expected.add(audit.expected_count)
                if snapshot.beat and snapshot.beat.state == "unlocked":
                    pll_expired = True
            if 11 <= elapsed < 12 and capture is None:
                window._tick()
                app.processEvents()
                capture = window.grab().toImage()
            for error in (snapshot.analysis_error, snapshot.kick_error, snapshot.beat_error,
                    snapshot.structure_error, snapshot.texture_error, snapshot.kick_verification_error, light.error):
                if error:
                    errors.add(error)
        sleep(0.005)
    status = window.runtime.status()
    snapshot = window.runtime.snapshot()
    report = dict(source="synthetic_structure_demo", effect="beat_pulse", physical_output=False,
        status=asdict(status), acquired_seconds=acquired, phrase_steps_without_kicks=sorted(phrases),
        confirmed_counts_during_pause=sorted(confirmed), expected_counts_during_pause=sorted(expected),
        peak_intensity_without_kick=max(intensities), phase_range=[min(phases), max(phases)],
        raw_pll_expired=pll_expired, final_grid=asdict(snapshot.structure.grid),
        continuity_errors=snapshot.continuity_errors, stage_geometries=sorted(geometry), errors=sorted(errors))
finally:
    window.close()
    end = monotonic() + 8
    while not window.closed_ready and monotonic() < end:
        app.processEvents()
        sleep(0.005)
if capture:
    capture.save(str(root / "preview-grid.png"))
report["closed_cleanly"] = window.closed_ready and not window.light_runtime.running
report["final_intensities_zero"] = all(s.intensity == 0 for s in window.light_runtime.snapshot().states)
(root / "docs" / "resultado-grid-v0.16.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
assert acquired < 2.5 and phrases == set(range(1, 9))
assert len(confirmed) == 1 and len(expected) >= 10
assert pll_expired and max(intensities) > 0.6 and max(phases) - min(phases) > 0.9
assert not errors and status.dropped_blocks == snapshot.continuity_errors == 0
assert len(geometry) == 1 and capture is not None
assert report["closed_cleanly"] and report["final_intensities_zero"]
