"""Integração nativa: captura sintética e relatório local; sem saída física."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu --disable-gpu-compositing --no-sandbox')
os.environ.setdefault('QT_QUICK_BACKEND','software')
os.environ.setdefault('QT_OPENGL','software')
import json
from pathlib import Path
import sys
from time import monotonic,sleep
import numpy as np
from PySide6.QtCore import QUrl
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
from beatlight import __version__
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE
import beatlight.audio.synthetic as synthetic

root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'tests'))
from drop_click_signals import click_scene
signal=click_scene()
def samples(t):
    return signal[np.minimum((t*48000).astype(int),len(signal)-1)]
synthetic.structure_demo_samples=samples
app=QApplication([]);app.setStyle('Fusion');app.setStyleSheet(STYLE)
app.setQuitOnLastWindowClosed(False)
if os.name=='nt':
    for name in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf'):
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
window=MainWindow(SettingsStore(root/'.runtime/drop-click-native/preferences.json'),Settings(source='structure_demo'))
window.show();window._navigate(7)
def pump(condition,timeout=25):
    end=monotonic()+timeout
    while monotonic()<end:
        app.processEvents()
        if condition():return
        sleep(.003)
    assert condition(),window.last_error
positions=set();first_drop=None;saved=False
report={'version':__version__,'synthetic_only':True,'physical_device_used':False,'connected_browser_used':False}
try:
    pump(lambda:not window.busy and bool(window.devices));window._start()
    pump(lambda:not window.busy and window.runtime.status().state=='running')
    def collect():
        global first_drop,saved
        snapshot=window.runtime.snapshot()
        if snapshot and snapshot.structure and snapshot.structure.state=='drop':
            structure=snapshot.structure
            if first_drop is None:first_drop=structure
            positions.add(structure.drop_kicks)
            if not saved:
                window._tick();app.processEvents()
                assert window.grab().save(str(root/'preview-drop-click-v0.29.png'))
                saved=True
        return window.runtime.status().elapsed>=16.8
    pump(collect)
    status=window.runtime.status();snapshot=window.runtime.snapshot()
    assert first_drop and first_drop.drop_evidence.click_supported
    assert positions==set(range(1,9)) and status.dropped_blocks==0
    assert not snapshot.structure_error and not snapshot.kick_error
    assert not window.pixel_page.usb.runtime.status().armed
    report.update(blocks=status.blocks,dropped_audio_blocks=status.dropped_blocks,
        drop_positions=sorted(positions),click_supported=True)
finally:
    window.close();pump(lambda:window.closed_ready)

# Teste do HTML que a aplicação exportou, usando o mesmo Qt do produto.
view=QWebEngineView();view.resize(1200,950);view.page().setAudioMuted(True)
loaded=[];load_errors=[]
view.page().loadingChanged.connect(lambda info:load_errors.append((info.errorCode(),info.errorString())) if info.errorCode() else None)
view.loadFinished.connect(loaded.append);view.show()
view.load(QUrl.fromLocalFile(str(root/'.runtime/replays/drop-v0.29-final/report.html')))
pump(lambda:bool(loaded));assert loaded[-1],load_errors
def evaluate(code):
    result=[];view.page().runJavaScript(code,result.append)
    pump(lambda:bool(result));return result[0]
pump(lambda:evaluate('document.querySelector("audio").readyState>=1'))
assert evaluate('document.querySelectorAll("svg").length')==4
assert abs(evaluate('document.querySelector("audio").duration')-17)<.02
assert '96.0 ms' in evaluate('document.body.innerText')
assert '21/21' in evaluate('document.body.innerText')
evaluate('var row=document.querySelector("svg");var rect=row.getBoundingClientRect();row.dispatchEvent(new MouseEvent("click",{clientX:rect.left+rect.width*.75,bubbles:true}));true;')
assert abs(evaluate('document.querySelector("audio").currentTime')-12.75)<.05
assert evaluate('document.querySelector("audio").paused') is True
for _ in range(60):
    app.processEvents()
    sleep(.01)  # Chromium entrega a pintura depois de os callbacks DOM terminarem.
assert view.grab().save(str(root/'preview-replay-v0.29.png'))
report.update(report_native_render=True,report_audio_metadata=True,report_seek=True,report_autoplay=False,passed=True)
view.close();view.deleteLater();app.processEvents()
(root/'docs'/f'resultado-replay-ui-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
