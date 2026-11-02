"""Kick Monitor com áudio sintético mascarado; não abre hardware nem USB."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
from pathlib import Path
import sys
from time import monotonic,sleep
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from beatlight import __version__
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE
import beatlight.audio.synthetic as synthetic

root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'tests'))
from kick_masking_signals import arrangement
signal,_=arrangement('held',duration=12)
def masked_samples(t):
    samples=signal[np.minimum((t*48000).astype(int),len(signal)-1)]
    return np.asarray(np.column_stack((samples,-samples)),dtype=np.float32)
synthetic.structure_demo_samples=masked_samples
app=QApplication([]);app.setStyle('Fusion');app.setStyleSheet(STYLE)
if os.name=='nt':
    for name in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
window=MainWindow(SettingsStore(root/'.runtime/kick-masking-qa/preferences.json'),Settings(source='structure_demo'))
window.show();window._navigate(4)
def pump(condition,timeout=15):
    end=monotonic()+timeout
    while monotonic()<end:
        app.processEvents()
        if condition():return
        sleep(.003)
    assert condition(),window.last_error
report={'version':__version__,'physical_device_used':False,'synthetic_only':True}
try:
    pump(lambda:not window.busy and bool(window.devices));window._start()
    pump(lambda:not window.busy and window.runtime.status().state=='running')
    pump(lambda:window.runtime.status().elapsed>=8)
    window._tick();app.processEvents();snapshot=window.runtime.snapshot();status=window.runtime.status()
    assert not snapshot.kick_error and not snapshot.structure_error
    assert snapshot.kick_verification.confirmed_count>=12 and snapshot.kicks.masked_count>=10
    assert status.dropped_blocks==0 and window.kick_table.columnCount()==6
    assert len(snapshot.kicks.masked_history)<=200
    assert not window.pixel_page.usb.runtime.status().armed
    window.grab().save(str(root/'preview-kicks-baixo-v0.27.png'))
    report.update(blocks=status.blocks,dropped_audio_blocks=status.dropped_blocks,raw_candidates=snapshot.kicks.count,
      confirmed_kicks=snapshot.kick_verification.confirmed_count,spectral_candidates=snapshot.kicks.masked_count,
      masked_history=len(snapshot.kicks.masked_history),last_processing_ms=snapshot.processing_ms)
finally:
    window.close();pump(lambda:window.closed_ready,20)
report['passed']=True
(root/'docs'/f'resultado-kick-masking-ui-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
