"""Qt/WebEngine + USB emulado: quatro GPIOs, quadros conjuntos e mapeamento salvo."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu --disable-gpu-compositing --no-sandbox')
os.environ.setdefault('QT_QUICK_BACKEND','software')
os.environ.setdefault('QT_OPENGL','software')
from collections import deque
from copy import deepcopy
import json,sys,tempfile
from pathlib import Path
from time import monotonic,sleep
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import QCoreApplication,QEvent
from beatlight import __version__
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.pixel.project import PixelProjectStore
from beatlight.pixel.usb import PixelUsbOutput
from beatlight.pixel.usb_protocol import BLACKOUT,CONFIG,PINS
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'tests'))
from pixel_usb_fake import FakeEsp32Port,INFO_MULTI
app=QApplication([]);app.setStyle('Fusion');app.setStyleSheet(STYLE)
if os.name=='nt':
    for name in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
report=dict(version=__version__,physical_device_used=False,emulated_serial=True,pins=list(PINS))
with tempfile.TemporaryDirectory(prefix='usb-four-',dir=root/'.runtime') as folder:
    directory=Path(folder);project=json.loads((root/'examples/ws2812-300.json').read_text(encoding='utf-8'))
    project['geometry']['lines']=[deepcopy(project['geometry']['lines'][0]) for _ in range(4)]
    project['strips']=[deepcopy(project['strips'][0]) for _ in range(4)]
    for i,count in enumerate((120,300,90,60)):
        project['geometry']['lines'][i].update(name=f'Fita {i+1} · {count}',leds=count,pixels=count,start={'x':150+i*300,'y':540},end={'x':150+i*300,'y':80})
        project['strips'][i].update(id=f'physical-{i}',profile='ws2811',effect='inherit',response='ambient')
    project['show'].update(mode='liquid',peakMode='off',strobes=False)
    PixelProjectStore(directory/'pixel-studio.json').save(project)
    window=MainWindow(SettingsStore(directory/'preferences.json'),Settings(source='synthetic'))
    panel=window.pixel_page.usb;devices=[]
    def device_factory(_):
        device=FakeEsp32Port(info=INFO_MULTI);device.frames=deque(maxlen=128);device.commands=deque(maxlen=256);devices.append(device);return device
    panel.runtime=PixelUsbOutput(device_factory);window.show();window._navigate(9)
    def pump(condition,timeout=20):
        end=monotonic()+timeout
        while monotonic()<end:
            app.processEvents()
            if condition():return
            sleep(.004)
        assert condition(),(window.pixel_page.notice.text(),panel.error,panel.runtime.status())
    def js(expression):
        result=[];window.pixel_page.webpage.runJavaScript('JSON.stringify('+expression+')',result.append)
        pump(lambda:bool(result));assert result[0];return json.loads(result[0])
    def frames(count=5):
        initial=panel.runtime.status().frames;pump(lambda:panel.runtime.status().frames>=initial+count)
        return bytes(devices[-1].frames[-1])
    def connect():
        pump(lambda:panel.runtime.closed and panel.connect_button.isEnabled());panel.connect_button.click()
        pump(lambda:panel.runtime.status().state=='connected');assert not panel.runtime.status().armed
    def activate():
        pump(lambda:panel.enable.isEnabled());panel.enable.click();return frames()
    try:
        pump(lambda:window.pixel_page.bridge.ready_state and not window.busy);window.timer.stop();panel.mode.setCurrentIndex(1)
        pump(lambda:panel.source.count()==4 and panel.prepare.isEnabled())
        for i in range(4):
            panel.sources[i].setCurrentIndex(panel.sources[i].findData(f'physical-{i}'));panel.output_enabled[i].setChecked(True)
            pump(lambda row=i:panel.prepares[row].isEnabled());panel.prepares[i].click();pump(lambda:not panel.preparing)
            assert not panel.error
        # A logical strip can feed two physical pins as exact copies.
        panel.sources[3].setCurrentIndex(panel.sources[3].findData('physical-0'))
        panel.port.clear();panel.port.addItem('EMULADO · nenhuma placa física','EMULATED');connect()
        assert panel.runtime.status().pixels==(120,300,90,120) and panel.runtime.status().protocol==2
        js('(BeatlightPixel.setInput("demo"),true)');payload=activate()
        assert len(payload)==1890 and payload[:360]==payload[-360:]
        assert all(any(payload[first:last]) for first,last in ((0,360),(360,1260),(1260,1530),(1530,1890)))
        report.update(counts=[120,300,90,120],payload_bytes=1890,distinct_lengths=True,exact_physical_copy=True)
        assert len(next(command.payload for command in devices[-1].commands if command.kind==CONFIG))==11
        before=js('BeatlightPixel.status().performance');frames(40);after=js('BeatlightPixel.status().performance')
        assert after['allocations']==before['allocations'] and after['rootAllocations']==before['rootAllocations']
        report['buffers_reused']=True
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        assert window.grab().save(str(root/'preview-quatro-saidas-v0.37.png'))
        panel.fold.setChecked(False);frames()
        assert window.grab().save(str(root/'preview-quatro-saidas-palco-v0.37.png'))
        window.showMinimized();frames(10);window.showNormal();report['minimized_output_continues']=True
        js('(BeatlightPixel.blackout(true),true)');pump(lambda:not any(devices[-1].frames[-1]))
        report['all_outputs_blackout']=True;js('(BeatlightPixel.blackout(false),true)');frames()
        panel.off.click();pump(lambda:devices[-1].commands[-1].kind==BLACKOUT)
        pump(lambda:panel.output_enabled[2].isEnabled());panel.output_enabled[2].setChecked(False)
        pump(lambda:panel.runtime.closed);connect();payload=activate()
        assert panel.active_pixels==(120,300,0,120) and len(payload)==1620 and payload[:360]==payload[-360:]
        report['disabled_output_omitted']=True
        panel.off.click();pump(lambda:devices[-1].commands[-1].kind==BLACKOUT)
        window.pixel_page.reload_preview();pump(lambda:window.pixel_page.bridge.ready_state and not window.pixel_page._reloading)
        assert not panel.runtime.status().armed and panel.active_pixels==(120,300,0,120)
        js('(BeatlightPixel.setInput("demo"),true)');activate()
        report.update(preview_reload_preserves_mapping=True,frames=panel.runtime.status().frames,fps=panel.runtime.status().fps)
    finally:
        window.timer.start();window.close();pump(lambda:window.closed_ready)
    assert all(device.closed and device.commands[-1].kind==BLACKOUT for device in devices)
    saved=json.loads((directory/'pixel-usb.json').read_text(encoding='utf-8'))
    assert [row['enabled'] for row in saved['outputs']]==[True,True,False,True]
    assert saved['outputs'][0]['strip_id']==saved['outputs'][3]['strip_id']=='physical-0'
    assert window.pixel_page.bridge.store.load()['geometry']==project['geometry']
    report.update(persisted_mapping=True,layout_preserved=True,closed_cleanly=True,passed=True)
(root/'docs'/f'resultado-pixel-four-outputs-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
