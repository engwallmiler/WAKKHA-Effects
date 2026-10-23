"""Renderiza o monitor real com uma fonte de teste; uso exclusivo de QA."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sys
from time import monotonic, sleep
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from beatlight.configuration.store import Settings, SettingsStore
from beatlight.ui.theme import STYLE
from beatlight.ui.window import MainWindow

app = QApplication([])
if os.name == "nt":
    for filename in ("segoeui.ttf", "segoeuib.ttf", "segoeuisl.ttf", "seguisym.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + filename)
app.setStyle("Fusion")
app.setStyleSheet(STYLE)
root = Path(__file__).resolve().parents[1]
window = MainWindow(SettingsStore(root / ".runtime" / "preview-preferences.json"), Settings(source="synthetic"))
window.resize(1440, 960)
window.show()
started = False
end = monotonic() + 7
while monotonic() < end:
    app.processEvents()
    if not started and not window.busy and window.devices:
        window._start()
        window.light_effect_combo.setCurrentIndex(window.light_effect_combo.findData("beat_chase"))
        window.light_arm_check.setChecked(True)
        started = True
    sleep(0.005)
for index, name in ((0, "preview.png"), (3, "preview-espectro.png"), (4, "preview-kicks.png"), (5, "preview-ritmo.png"), (6, "preview-iluminacao.png"), (7, "preview-palco.png"), (2, "preview-configuracoes.png")):
    window._navigate(index)
    window._tick()
    app.processEvents()
    window.grab().save(str(root / name))
    print("Preview:", root / name)
window.close()
end = monotonic() + 6
while not window.closed_ready and monotonic() < end:
    app.processEvents()
    sleep(0.005)
assert window.closed_ready, "Encerramento incompleto"
