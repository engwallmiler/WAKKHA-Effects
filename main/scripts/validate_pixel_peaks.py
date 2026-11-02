"""Picos e fades no Canvas nativo e no USB emulado; não abre hardware real."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu --disable-gpu-compositing --no-sandbox')
os.environ.setdefault('QT_QUICK_BACKEND','software')
os.environ.setdefault('QT_OPENGL','software')
from collections import deque
import hashlib,json,sys
from pathlib import Path
from time import monotonic,sleep
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from beatlight import __version__
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.pixel.usb import PixelUsbOutput
from beatlight.pixel.usb_protocol import BLACKOUT
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'tests'))
from pixel_usb_fake import FakeEsp32Port
app=QApplication([]);app.setStyle('Fusion');app.setStyleSheet(STYLE)
if os.name=='nt':
    for name in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
window=MainWindow(SettingsStore(root/'.runtime/pixel-peaks/preferences.json'),Settings(source='synthetic'))
panel=window.pixel_page.usb;device=FakeEsp32Port();device.frames=deque(maxlen=128);device.commands=deque(maxlen=256)
panel.runtime=PixelUsbOutput(lambda name:device)
window.show();window._navigate(9)
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
def frames(count=4):
    initial=panel.runtime.status().frames;pump(lambda:panel.runtime.status().frames>=initial+count)
    return bytes(device.frames[-1])
def control(name,value):
    js('(()=>{const e=document.getElementById('+json.dumps(name)+');e.value='+json.dumps(str(value))+';e.dispatchEvent(new Event('+json.dumps('input' if name=='peakLevel' else 'change')+'));return true;})()')
report=dict(version=__version__,physical_device_used=False,emulated_serial=True,levels=[],patterns=[])
try:
    pump(lambda:window.pixel_page.bridge.ready_state and not window.busy)
    window.timer.stop();panel.mode.setCurrentIndex(1)
    p=json.loads((root/'examples/uma-fita-300-6-barras.json').read_text(encoding='utf-8'))
    p['show'].update(mode='breathe',brightness=1,peakMode='on',peakEvery=8,peakLevel=0,peakStyle='flood',peakColor='white',strobes=False)
    for strip in p['strips']:strip.update(brightness=1,effect='inherit',palette='inherit',response='hybrid')
    js('BeatlightPixel.applyProject('+json.dumps(p)+')')
    pump(lambda:panel.source.count()==1 and panel.connect_button.isEnabled())
    panel.port.clear();panel.port.addItem('EMULADO · sem placa física','EMULATED')
    panel.connect_button.click();pump(lambda:panel.runtime.status().state=='connected')
    js('(()=>{window.qaBeat=32;window.qaFeed=()=>BeatlightPixel.receive({version:1,at:100,active:true,audible:true,kick:null,clock:{beat:qaBeat,bpm:128,source:"link"},music:{state:"groove",energy:.3,tension:.1,brightness:.4,drop_id:0,drop_kicks:0,bass:0,density:0,activity:0}});BeatlightPixel.setInput("live");BeatlightPixel.arm(true);qaFeed();BeatlightPixel.syncPeak();qaBeat=BeatlightPixel.status().beat+.02;qaFeed();window.qaTimer=setInterval(qaFeed,25);return true;})()')
    pump(lambda:panel.enable.isEnabled());panel.enable.click();pump(lambda:panel.runtime.status().frames>=4)
    panel.fold.setChecked(False)
    before=js('BeatlightPixel.status().performance')
    for level in (0,25,50,75,100):
        control('peakLevel',level);payload=frames()
        report['levels'].append(dict(percent=level,mean=sum(payload)/len(payload),minimum=min(payload),maximum=max(payload)))
    assert len(payload)==900 and all(v==255 for v in payload)
    assert all(a['mean']<b['mean'] for a,b in zip(report['levels'],report['levels'][1:]))
    for _ in range(10):app.processEvents();sleep(.01)
    assert window.grab().save(str(root/'preview-pico-maximo-v0.33.png'))
    for style in ('wave','blocks'):
        control('peakStyle',style);payload=frames()
        assert max(payload)>=250 and min(payload)<240
        report['patterns'].append(dict(style=style,maximum=max(payload),sha256=hashlib.sha256(payload).hexdigest()))
    control('peakLevel',0);js('(document.getElementById("quickContinuous").click(),qaBeat+=8,qaFeed(),true)');frames(8)
    payload=bytes(device.frames[-1]);assert all(max(payload[p:p+3])>0 for p in range(0,900,3))
    report['continuous']=js('BeatlightPixel.status()')
    assert report['continuous']['minimumBeats']==32
    assert js('BeatlightPixel.project().show.compositionStyle')=='continuous'
    for _ in range(10):app.processEvents();sleep(.01)
    assert window.grab().save(str(root/'preview-continuo-v0.33.png'))
    after=js('BeatlightPixel.status().performance')
    assert after['allocations']==before['allocations'] and after['rootAllocations']==before['rootAllocations']
    report['buffers_reused']=True
    window.showMinimized();frames(8);report['minimized_output_continues']=True
    window.showNormal();js('(BeatlightPixel.blackout(true),true)');pump(lambda:not any(device.frames[-1]))
    report['blackout_zero']=True
    report.update(frames=panel.runtime.status().frames,fps=panel.runtime.status().fps)
    js('(clearInterval(qaTimer),true)')
finally:
    window.timer.start();window.close();pump(lambda:window.closed_ready)
assert device.closed and device.commands[-1].kind==BLACKOUT
saved=window.pixel_page.bridge.store.load()
assert saved['show']['compositionStyle']=='continuous' and saved['show']['peakStyle']=='blocks'
report.update(closed_cleanly=True,persisted_controls=True,passed=True)
(root/'docs'/f'resultado-pixel-peaks-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
