"""Verifica a grade acústica inteira na GUI, sem áudio/USB físicos."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
from pathlib import Path
import sys
from time import monotonic, sleep
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from beatlight import __version__
from beatlight.configuration.store import Settings, SettingsStore
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE
import beatlight.audio.synthetic as synthetic

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/'tests'))
from test_stable_audio_grid import early_bass_arrangement
signal, _ = early_bass_arrangement(duration=14)

def samples(t):
    x = signal[np.minimum((t*48000).astype(int), len(signal)-1)]
    return np.asarray(np.column_stack((x, -x)), dtype=np.float32)

synthetic.structure_demo_samples = samples
app = QApplication([])
app.setStyle('Fusion')
app.setStyleSheet(STYLE)
if os.name == 'nt':
    for name in ('segoeui.ttf', 'segoeuib.ttf', 'seguisym.ttf'):
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
window = MainWindow(SettingsStore(root/'.runtime/audio-grid-qa/preferences.json'), Settings(source='structure_demo'))
window.show()
window._navigate(4)

def pump(condition, timeout=20):
    end = monotonic()+timeout
    while monotonic()<end:
        app.processEvents()
        if condition():
            return
        sleep(.003)
    assert condition(), window.last_error

report = {'version':__version__, 'synthetic_only':True, 'physical_device_used':False, 'external_clock_used':False}
try:
    pump(lambda: not window.busy and bool(window.devices))
    window._start()
    pump(lambda: not window.busy and window.runtime.status().state=='running')
    pump(lambda: window.runtime.status().elapsed>=8)
    window._tick()
    app.processEvents()
    snapshot = window.runtime.snapshot()
    status = window.runtime.status()
    grid = snapshot.structure.grid
    assert not snapshot.kick_error and not snapshot.structure_error
    assert grid.tempo_locked and grid.period==60/128 and snapshot.kicks.grid_guided
    assert snapshot.kick_verification.confirmed_count>=14 and snapshot.kicks.offgrid_count>=3
    assert status.dropped_blocks==0
    assert not window.pixel_page.usb.runtime.status().armed
    assert window.grab().save(str(root/'preview-grade-audio-v0.28.png'))
    window._navigate(5)
    window._tick()
    assert window.rhythm_metrics['bpm'].text()=='128'
    window.kick_grid_settings.click()
    assert window.pages.currentIndex()==2 and window.beat_mode_combo.currentData()=='integer'
    assert window.pages.widget(2).verticalScrollBar().value()>0
    report.update(blocks=status.blocks, dropped_audio_blocks=status.dropped_blocks,
        raw_candidates=snapshot.kicks.count, confirmed_kicks=snapshot.kick_verification.confirmed_count,
        offgrid_attacks=snapshot.kicks.offgrid_count, period=grid.period, bpm=60/grid.period,
        tempo_locked=grid.tempo_locked, last_processing_ms=snapshot.processing_ms,
        grid_settings_shortcut=True, table_columns=window.kick_table.columnCount())
finally:
    window.close()
    pump(lambda: window.closed_ready)
report['passed'] = True
(root/'docs'/f'resultado-grade-audio-ui-v{__version__}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
