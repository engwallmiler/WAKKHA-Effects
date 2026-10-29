"""Qt/Canvas/motor/USB emulado: não abre uma porta física nem modifica AppData."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu --disable-gpu-compositing --no-sandbox')
os.environ.setdefault('QT_QUICK_BACKEND','software')
os.environ.setdefault('QT_OPENGL','software')
import json
from pathlib import Path
import sys
from time import monotonic,sleep
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from beatlight import __version__
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE
from beatlight.pixel.usb import PixelUsbOutput
from beatlight.pixel.usb_protocol import FRAME,BLACKOUT,CONFIG,OutputConfig

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tests'))
from pixel_usb_fake import FakeEsp32Port

app=QApplication([]);app.setStyle('Fusion');app.setStyleSheet(STYLE)
if os.name=='nt':
    for name in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
window=MainWindow(SettingsStore(root/'.runtime/pixel-usb-qa/preferences.json'),Settings(source='synthetic'))
panel=window.pixel_page.usb
device=FakeEsp32Port();panel.runtime=PixelUsbOutput(lambda name:device)
window.show();window._navigate(9)

def pump(condition,timeout=15):
    end=monotonic()+timeout
    while monotonic()<end:
        app.processEvents()
        if condition():return
        sleep(.005)
    assert condition(),f'USB QA: {panel.status.text()} / {panel.error} / {panel.runtime.status()}'

def js(expression):
    result={}
    window.pixel_page.webpage.runJavaScript('JSON.stringify('+expression+')',lambda value:result.update(value=value))
    pump(lambda:'value' in result)
    assert result['value'],window.pixel_page.notice.text()
    return json.loads(result['value'])

report={'physical_device_used':False,'emulated_serial':True,'pixels':300,'effects':[]}
try:
    pump(lambda:window.pixel_page.bridge.ready_state)
    panel.mode.setCurrentIndex(1)
    project=json.loads((root/'examples/ws2812-300.json').read_text(encoding='utf-8'))
    js('BeatlightPixel.applyProject('+json.dumps(project)+')')
    pump(lambda:panel.source.count()==1 and panel.refresh.isEnabled())
    panel.prepare.click();pump(lambda:js('BeatlightPixel.project().geometry.lines[0].pixels')==300)
    pump(lambda:panel.connect_button.isEnabled())
    panel.port.clear();panel.port.addItem('EMULADO · nenhuma placa física','EMULATED')
    panel.connect_button.click();pump(lambda:panel.runtime.status().state=='connected')
    assert not panel.runtime.status().armed and not device.frames
    assert next(c.payload for c in device.commands if c.kind==CONFIG)==OutputConfig().payload()
    js('(BeatlightPixel.setInput("demo"),true)')
    pump(lambda:panel.enable.isEnabled());panel.enable.click()
    pump(lambda:panel.runtime.status().frames>=5)
    effects=['ambient','pulse','chase','mirror','wave','helix','rain','drop','comet','scanner','sparkle','meteor','fire','rainbow','blocks','bounce','ripple','equalizer','snake','aurora','weave','orbit','shards','tide','lattice','vortex']
    for effect in effects:
        p=js('BeatlightPixel.project()');p['strips'][0].update(effect=effect,response='ambient')
        js('BeatlightPixel.applyProject('+json.dumps(p)+')')
        count=panel.runtime.status().frames
        pump(lambda:panel.runtime.status().frames>=count+2)
        assert len(device.frames[-1])==900
        report['effects'].append(effect)
    assert any(any(frame) for frame in device.frames)
    count=panel.runtime.status().frames
    js('(document.body.classList.contains("presentation")&&document.getElementById("presentationBtn").click(),document.getElementById("geometryFold").open=true,document.getElementById("stripEffect").scrollIntoView({block:"center",behavior:"instant"}),true)')
    pump(lambda:panel.runtime.status().frames>=count+8)
    report['scroll_continues']=True
    count=panel.runtime.status().frames
    window._navigate(0);pump(lambda:panel.runtime.status().frames>=count+8)
    report['other_page_continues']=True
    window._navigate(9)
    js('(BeatlightPixel.blackout(true),true)')
    pump(lambda:device.frames and not any(device.frames[-1]))
    report['blackout_zero']=True
    js('(BeatlightPixel.blackout(false),document.getElementById("geometryFold").open=false,!document.body.classList.contains("presentation")&&document.getElementById("presentationBtn").click(),scrollTo(0,0),true)')
    panel.off.click();pump(lambda:device.commands[-1].kind==BLACKOUT)
    assert not panel.runtime.status().armed
    report['physical_off']=True
    pump(lambda:not panel.enable.isChecked());panel.enable.click();pump(lambda:panel.runtime.status().armed)
    count=panel.runtime.status().frames;pump(lambda:panel.runtime.status().frames>=count+8 and panel.enable.text()=='Saída física ATIVA')
    window.grab().save(str(root/'preview-pixel-usb.png'))
    report.update(frames=panel.runtime.status().frames,fps=panel.runtime.status().fps,source='ESP32 DevKit / WROOM-32, GPIO 18, GRB')
finally:
    window.close();pump(lambda:window.closed_ready)
    app.processEvents()
report['closed_cleanly']=window.closed_ready
report['close_blackout']=device.closed and device.commands[-1].kind==BLACKOUT
assert report['close_blackout']
(root/'docs'/f'resultado-pixel-usb-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
