"""Prévia nativa do monitor com dados acústicos sintéticos e nenhuma saída."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
from pathlib import Path
import sys
from time import monotonic,sleep
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from beatlight import __version__
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.dsp.pipeline import AudioAnalyzer
from beatlight.ui.kicks import update_kick_view
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE

root = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tests'))
from peak_grid_signals import masked_groove
from test_kicks import blocks

analyzer = AudioAnalyzer(beat_config=Settings().beat_config())
chosen = None
for block in blocks(masked_groove(bass=.95)[0]):
    snapshot = analyzer.process(block)
    if snapshot.kick_verification and any(e.evidence=='grid-peak' for e in snapshot.kick_verification.confirmed_events):
        chosen = snapshot
        break
assert chosen and not chosen.structure_error
app = QApplication([])
app.setStyle('Fusion');app.setStyleSheet(STYLE)
if os.name=='nt':
    for name in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf'):
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
window = MainWindow(SettingsStore(root/'.runtime/peak-grid-qa/preferences.json'),Settings(source='synthetic'))
window.show();window._navigate(4)

def pump(condition,timeout=10):
    end = monotonic()+timeout
    while monotonic()<end:
        app.processEvents()
        if condition():return
        sleep(.005)
    assert condition()

report = dict(version=__version__,synthetic_only=True,physical_device_used=False)
try:
    pump(lambda:not window.busy)
    # Desliga só o refresh desta sessão de inspeção; não inicia captura/USB.
    window.timer.stop()
    update_kick_view(window,chosen,window.runtime.status(),True)
    end = monotonic()+.5
    pump(lambda:monotonic()>=end)
    sensors = [window.kick_table.item(row,4).text() for row in range(window.kick_table.rowCount())]
    assert 'Pico + BPM' in sensors
    assert 'Grade de picos' in window.kick_confirmation_detail.text()
    assert not window.pixel_page.usb.runtime.status().armed
    assert window.grab().save(str(root/'preview-peak-grid-v0.31.png'))
    report.update(passed=True,table_columns=window.kick_table.columnCount(),sensors=sensors,
        detail=window.kick_confirmation_detail.text(),preview='preview-peak-grid-v0.31.png',
        period=chosen.structure.grid.period,peak_anchor=chosen.structure.peak_grid.anchor_at)
finally:
    window.close();pump(lambda:window.closed_ready)
(root/'docs/resultado-peak-grid-ui-v0.31.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
