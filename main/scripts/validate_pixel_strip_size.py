"""Preparação de 120 LEDs, troca de fonte e persistência em Qt/USB emulado."""
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
from beatlight import __version__
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.pixel.project import PixelProjectStore
from beatlight.pixel.usb import PixelUsbOutput
from beatlight.pixel.usb_protocol import BLACKOUT
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'tests'))
from pixel_usb_fake import FakeEsp32Port
app=QApplication([]);app.setStyle('Fusion');app.setStyleSheet(STYLE)
if os.name=='nt':
    for name in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
report=dict(version=__version__,physical_device_used=False,emulated_serial=True)
with tempfile.TemporaryDirectory(prefix='usb-size-',dir=root/'.runtime') as folder:
    directory=Path(folder)
    project=json.loads((root/'examples/ws2812-300.json').read_text(encoding='utf-8'))
    project['geometry']['lines']=[deepcopy(project['geometry']['lines'][0]) for _ in range(2)]
    project['strips']=[deepcopy(project['strips'][0]) for _ in range(2)]
    project['strips'][0]['id']='reference-300';project['strips'][1].update(id='physical-120',profile='ws2811')
    project['geometry']['lines'][0].update(name='Referência 300',start={'x':350,'y':540},end={'x':350,'y':80})
    project['geometry']['lines'][1].update(name='Minha fita 120',leds=120,pixels=120,start={'x':850,'y':540},end={'x':850,'y':80})
    project['show'].update(mode='liquid',peakMode='off',strobes=False)
    PixelProjectStore(directory/'pixel-studio.json').save(project)
    (directory/'pixel-usb.json').write_text(json.dumps(dict(strip_id='physical-120',brightness=64,milliamps=2000)),encoding='utf-8')
    window=MainWindow(SettingsStore(directory/'preferences.json'),Settings(source='synthetic'))
    panel=window.pixel_page.usb;device=FakeEsp32Port();device.frames=deque(maxlen=128);device.commands=deque(maxlen=256)
    panel.runtime=PixelUsbOutput(lambda name:device);window.show();window._navigate(9)

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
        return bytes(device.frames[-1])

    try:
        pump(lambda:window.pixel_page.bridge.ready_state and not window.busy)
        window.timer.stop();panel.mode.setCurrentIndex(1)
        pump(lambda:panel.source.count()==2 and panel.prepare.isEnabled())
        assert panel.source.currentData()=='physical-120' and panel.pixel_count.value()==120
        panel.port.clear();panel.port.addItem('EMULADO · sem placa física','EMULATED')
        panel.connect_button.click();pump(lambda:panel.runtime.status().state=='connected')
        assert not device.frames and not panel.runtime.status().armed
        panel.prepare.click();pump(lambda:not panel.preparing)
        assert not panel.error and 'Pronta: Minha fita 120' in panel.source_info.text()
        after=js('BeatlightPixel.project()')
        assert after['geometry']==project['geometry'] and after['strips'][1]['profile']=='ws2812'
        assert after['strips'][1]['id']=='physical-120' and after['strips'][0]==project['strips'][0]
        report.update(preparation_preserves_layout=True,selected_source_preserved=True,real_pixels=120)
        js('(BeatlightPixel.setInput("demo"),BeatlightPixel.arm(true),true)')
        pump(lambda:panel.enable.isEnabled());panel.enable.click();payload=frames()
        assert len(payload)==900 and any(payload[:360]) and payload[360:]==bytes(540)
        assert js('BeatlightPixel.outputFrame("physical-120").data.length')==360
        report.update(short_output_lit=True,unused_addresses_zero=True)
        for _ in range(6):app.processEvents();sleep(.01)
        assert window.grab().save(str(root/'preview-fita-120-v0.36.png'))
        panel.off.click();pump(lambda:device.commands[-1].kind==BLACKOUT)
        pump(lambda:panel.source.isEnabled());panel.source.setCurrentIndex(panel.source.findData('reference-300'))
        panel.enable.click();payload=frames();assert any(payload[360:])
        panel.off.click();pump(lambda:panel.source.isEnabled())
        panel.source.setCurrentIndex(panel.source.findData('physical-120'));panel.enable.click()
        payload=frames();assert any(payload[:360]) and payload[360:]==bytes(540)
        report['switch_300_to_120_clears_tail']=True
        window.showMinimized();payload=frames(8);assert any(payload[:360]) and not any(payload[360:])
        report['minimized_output_continues']=True
        window.showNormal();panel.off.click();pump(lambda:device.commands[-1].kind==BLACKOUT)
        window.pixel_page.reload_preview()
        pump(lambda:window.pixel_page.bridge.ready_state and not window.pixel_page._reloading)
        restored=js('BeatlightPixel.project()')
        assert restored['geometry']==project['geometry'] and restored['strips'][1]['profile']=='ws2812'
        assert panel.source.currentData()=='physical-120' and not panel.runtime.status().armed
        js('(BeatlightPixel.setInput("demo"),true)');pump(lambda:panel.enable.isEnabled())
        panel.enable.click();payload=frames();assert not any(payload[360:])
        report.update(reload_preserves_120=True,reload_requires_manual_activation=True,frames=panel.runtime.status().frames,fps=panel.runtime.status().fps)
    finally:
        window.timer.start();window.close();pump(lambda:window.closed_ready)
    assert device.closed and device.commands[-1].kind==BLACKOUT
    saved=window.pixel_page.bridge.store.load()
    assert saved['geometry']==project['geometry'] and saved['strips'][1]['profile']=='ws2812'
    assert json.loads((directory/'pixel-usb.json').read_text(encoding='utf-8'))['strip_id']=='physical-120'
    report.update(persistence_verified=True,closed_cleanly=True,passed=True)
(root/'docs'/f'resultado-pixel-strip-size-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
