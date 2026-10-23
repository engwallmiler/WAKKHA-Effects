"""Prévia local da página Link; não ativa rede, captura ou luzes."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
from time import monotonic, sleep
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
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
window = MainWindow(SettingsStore(root / ".runtime" / "preview-link" / "preferences.json"), Settings(source="synthetic"))
try:
    window.show()
    end = monotonic() + 5
    while window.busy and monotonic() < end:
        app.processEvents()
        sleep(.01)
    window._navigate(8)
    app.processEvents()
    assert window.link_runtime.snapshot().state == "disabled"
    assert window.runtime.status().state == "stopped"
    assert window.grab().save(str(root / "preview-link.png"))
    print("Link preview: disabled; audio: stopped; network: not activated")
finally:
    window.close()
    end = monotonic() + 8
    while not window.closed_ready and monotonic() < end:
        app.processEvents()
        sleep(.01)
    assert window.closed_ready
