"""Native Qt/WebEngine failure injection. Synthetic audio / fake USB only."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu --disable-gpu-compositing --no-sandbox')
os.environ.setdefault('QT_OPENGL','software')
from collections import deque
from datetime import datetime
import json
from pathlib import Path
import sys,tempfile
from time import monotonic,sleep
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog
from PySide6.QtGui import QFontDatabase
from beatlight import __version__
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.pixel.project import PixelProjectStore
from beatlight.pixel.usb import PixelUsbOutput
from beatlight.pixel.usb_protocol import BLACKOUT,FRAME
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE
from beatlight.diagnostics.pc_time import local_time

root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'tests'))
from pixel_usb_fake import FakeEsp32Port,INFO_MULTI
app=QApplication([]);report={'version':__version__,'physical_device_used':False,'fake_usb':True}
app.setStyle('Fusion');app.setStyleSheet(STYLE)
if os.name=='nt':
    for name in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
with tempfile.TemporaryDirectory(prefix='output-diagnostics-',dir=root/'.runtime') as folder:
    directory=Path(folder)
    project=json.loads((root/'examples/ws2812-300.json').read_text(encoding='utf-8'))
    project['geometry']['lines'][0].update(leds=120,pixels=120)
    project['show'].update(mode='auto',effectMix='single',peakMode='off')
    PixelProjectStore(directory/'pixel-studio.json').save(project)
    window=MainWindow(SettingsStore(directory/'preferences.json'),Settings(source='synthetic'))
    panel=window.pixel_page.usb;devices=[]
    def factory(_):
        device=FakeEsp32Port(info=INFO_MULTI);device.frames=deque(maxlen=128);device.commands=deque(maxlen=256);devices.append(device);return device
    panel.runtime=PixelUsbOutput(factory);window.show();window._navigate(9)
    def pump(condition,timeout=15):
        end=monotonic()+timeout
        while monotonic()<end:
            app.processEvents()
            if condition():return
            sleep(.003)
        assert condition(),(panel.error,panel.runtime.status(),list(window.pixel_page.render_errors))
    def settle(seconds):
        end=monotonic()+seconds;pump(lambda:monotonic()>=end,seconds+2)
    def js(expression):
        result={};window.pixel_page.webpage.runJavaScript('JSON.stringify('+expression+')',lambda value:result.update(value=value))
        pump(lambda:'value' in result);return json.loads(result['value'])
    def events():return window.output_journal.snapshot()['events']
    def code_count(code):return sum(row['code']==code for row in events())
    def stall(ms):window.pixel_page.webpage.runJavaScript(f'(()=>{{const until=performance.now()+{ms};while(performance.now()<until){{}};return true}})()')
    try:
        pump(lambda:window.pixel_page.bridge.ready_state and not window.busy)
        panel.mode.setCurrentIndex(1);pump(lambda:panel.source.count()>0)
        for source,enabled in zip(panel.sources,panel.output_enabled):source.setCurrentIndex(0);enabled.setChecked(True)
        panel.port.clear();panel.port.addItem('USB EMULADO','FAKE-COM');panel._connect();pump(lambda:panel.runtime.status().state=='connected')
        js('(BeatlightPixel.setInput("demo"),BeatlightPixel.arm(true),true)')
        panel._arm(True);pump(lambda:panel.runtime.status().frames>=3)
        assert panel.active_pixels==(120,)*4 and len(devices[-1].frames[-1])==1440
        initial=panel.runtime.status().frames;stall(400)
        pump(lambda:code_count('output.recovered')>=1)
        assert panel.runtime.status().armed and code_count('output.frame_timeout')==0
        pump(lambda:panel.runtime.status().frames>initial+2)
        report['400ms_renderer_stall_recovers_without_rearm']=True
        before=code_count('output.recovered');sleep(.35)
        pump(lambda:code_count('output.recovered')>before)
        assert panel.runtime.status().armed
        report['350ms_gui_stall_recovers_without_rearm']=True
        stall(1100);pump(lambda:not panel.runtime.status().armed)
        pump(lambda:panel._inflight is None)
        assert code_count('output.frame_timeout')>=1 and devices[-1].commands[-1].kind==BLACKOUT
        before=panel.runtime.status().frames;settle(.2);assert panel.runtime.status().frames==before
        panel._arm(True);pump(lambda:panel.runtime.status().frames>before)
        assert window.output_journal.snapshot()['last_incident']['code']=='output.frame_timeout'
        report['persistent_stall_requires_manual_rearm']=True
        before=panel.runtime.status().frames
        chooser=QFileDialog(window);chooser.setOption(QFileDialog.Option.DontUseNativeDialog);chooser.show()
        settle(.85);chooser.close()
        assert panel.runtime.status().armed and panel.runtime.status().frames>before+3
        report['qt_file_dialog_keeps_usb_frames_running']=True
        window.pixel_page.logs_button.click();dialog=window.pixel_page._log_dialog
        before=panel.runtime.status().frames;settle(.25)
        assert dialog.timer.isActive() and panel.runtime.status().frames>before
        dialog.search.setText('frame_timeout');assert dialog.table.rowCount()>=1
        dialog.table.selectRow(0);settle(.1)
        assert dialog.grab().save(str(root/f'preview-output-logs-v{__version__}.png'))
        export=directory/'diagnostic.json';dialog.export_to(export)
        pump(lambda:export.exists() and dialog.export_button.isEnabled())
        bundle=json.loads(export.read_text(encoding='utf-8'))
        assert bundle['last_incident']['code']=='output.frame_timeout' and bundle['health']
        assert all(datetime.fromisoformat(row['time']).utcoffset()==local_time(datetime.fromisoformat(row['time']).timestamp()).utcoffset() for row in bundle['events'])
        report['pc_local_time_example']=bundle['last_incident']['time']
        dialog.close();assert not dialog.timer.isActive()
        report['nonmodal_logs_export_local_time_and_previous_cause']=True
        devices[-1].allow_ack.clear();pump(lambda:panel.runtime.closed)
        fault=next(row for row in reversed(events()) if row['code']=='usb.transport_error')
        assert fault['context']['command']==FRAME and fault['context']['exception']=='TimeoutError'
        assert not panel.runtime.status().armed and panel.runtime.status().state=='error'
        report['missing_ack_closes_usb_and_records_command']=True
        report['event_counts']={code:code_count(code) for code in sorted({r['code'] for r in events()})}
        report['health_samples']=len(bundle['health']);report['errors']=list(window.pixel_page.render_errors)
        assert not report['errors']
    finally:
        window.close();pump(lambda:window.closed_ready,20)
    assert window.output_journal.closed
    report['closed_cleanly']=True;report['passed']=True
(root/'docs'/f'resultado-output-diagnostics-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
