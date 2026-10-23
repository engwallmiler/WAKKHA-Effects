"""Captura dos controles manuais RGBW, sem captura de áudio ou saída física."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
from time import monotonic, sleep
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from beatlight.configuration.store import Settings, SettingsStore
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE
root = Path(__file__).resolve().parents[1]
app = QApplication([])
if os.name == "nt":
    for name in ("segoeui.ttf", "segoeuib.ttf", "segoeuisl.ttf", "seguisym.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + name)
app.setStyle("Fusion")
app.setStyleSheet(STYLE)
window = MainWindow(SettingsStore(root / ".runtime" / "rgbw-preview-preferences.json"),
    Settings(source="synthetic", light_effect="orchestrated_show", light_transition_ms=0))
window.show()
window._navigate(6)
end = monotonic() + 5
while window.busy and monotonic() < end:
    app.processEvents()
    sleep(.005)
try:
    window.light_manual_check.setChecked(True)
    window.light_rgbw_check.setChecked(True)
    for key, value in (("manual_red",0), ("manual_green",0), ("manual_blue",0), ("manual_white",100)):
        window.light_manual_spins[key].setValue(value)
    window.light_arm_check.setChecked(True)
    end = monotonic() + 2
    while monotonic() < end:
        app.processEvents()
        if all(s.white == 1 for s in window.light_runtime.snapshot().states): break
        sleep(.005)
    window._tick()
    app.processEvents()
    top = window.grab().toImage()
    window.pages.widget(6).ensureWidgetVisible(window.light_table)
    app.processEvents()
    bottom = window.grab().toImage()
    assert window.light_table.item(0,6).text() == "100%"
finally:
    window.close()
    end = monotonic() + 8
    while not window.closed_ready and monotonic() < end:
        app.processEvents()
        sleep(.005)
top.save(str(root / "preview-rgbw-controles.png"))
bottom.save(str(root / "preview-rgbw-canais.png"))
assert window.closed_ready and all(s.white == 0 for s in window.light_runtime.snapshot().states)
print("RGBW manual: R=G=B=0, W=100%; coluna W conferida; encerramento com W=0.")
