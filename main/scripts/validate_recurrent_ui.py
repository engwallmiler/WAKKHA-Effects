"""Inspeção nativa do reaprendizado; sem captura ou saída físicas."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json,sys
from pathlib import Path
from time import monotonic,sleep
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from beatlight import __version__
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.dsp.pipeline import AudioAnalyzer
from beatlight.ui.kicks import update_kick_view
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tests'))
from recurrent_profile_signals import changed_kick_scene
from test_kicks import blocks

a=AudioAnalyzer(beat_config=Settings().beat_config());chosen=None
for block in blocks(changed_kick_scene()[0]):
    r=a.process(block)
    if r.kick_verification and any(e.evidence=='grid-profile' for e in r.kick_verification.confirmed_events):
        chosen=r;break
assert chosen and chosen.structure.kick_recovery.relearns==1
app=QApplication([]);app.setStyle('Fusion');app.setStyleSheet(STYLE)
if os.name=='nt':
    for name in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf'):
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
window=MainWindow(SettingsStore(root/'.runtime/recurrent-qa/preferences.json'),Settings(source='synthetic'))
window.show();window._navigate(4)
def pump(condition,timeout=10):
    end=monotonic()+timeout
    while monotonic()<end:
        app.processEvents()
        if condition():return
        sleep(.005)
    assert condition()
report=dict(version=__version__,synthetic_only=True,physical_device_used=False)
try:
    pump(lambda:not window.busy)
    window.timer.stop();update_kick_view(window,chosen,window.runtime.status(),True)
    end=monotonic()+.5;pump(lambda:monotonic()>=end)
    sensors=[window.kick_table.item(row,4).text() for row in range(window.kick_table.rowCount())]
    assert 'Perfil + grade' in sensors
    assert 'Perfil recorrente ativo' in window.kick_confirmation_detail.text()
    assert not window.pixel_page.usb.runtime.status().armed
    assert window.grab().save(str(root/'preview-recurrent-v0.32.png'))
    report.update(passed=True,sensors=sensors,detail=window.kick_confirmation_detail.text(),
        bpm=60/chosen.structure.grid.period,relearns=chosen.structure.kick_recovery.relearns)
finally:
    window.close();pump(lambda:window.closed_ready)
(root/'docs/resultado-recurrent-ui-v0.32.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
