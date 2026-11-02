"""Ondas orgânicas no Canvas Qt e USB emulado de 300 pixels; sem hardware."""
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
window=MainWindow(SettingsStore(root/'.runtime/pixel-flow/preferences.json'),Settings(source='synthetic'))
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
def frames(count=6):
    initial=panel.runtime.status().frames;pump(lambda:panel.runtime.status().frames>=initial+count)
    return bytes(device.frames[-1])
def control(name,value):
    js('(()=>{const e=document.getElementById('+json.dumps(name)+');e.value='+json.dumps(str(value))+';e.dispatchEvent(new Event("input"));return true;})()')
def digest(data):return hashlib.sha256(data).hexdigest()
report=dict(version=__version__,physical_device_used=False,emulated_serial=True,patterns=[])
try:
    pump(lambda:window.pixel_page.bridge.ready_state and not window.busy)
    window.timer.stop();panel.mode.setCurrentIndex(1)
    project=json.loads((root/'examples/uma-fita-300-6-barras.json').read_text(encoding='utf-8'))
    project['show'].update(mode='liquid',brightness=1,peakMode='off',flowDepth=1,flowSpeed=1,
        palette='primaries',musicColors=False,colorBehavior='scene',strobes=False,changeMode='hold')
    for strip in project['strips']:strip.update(brightness=1,effect='inherit',palette='inherit',response='hybrid')
    js('BeatlightPixel.applyProject('+json.dumps(project)+')')
    pump(lambda:panel.source.count()==1 and panel.connect_button.isEnabled())
    panel.port.clear();panel.port.addItem('EMULADO · sem placa física','EMULATED')
    panel.connect_button.click();pump(lambda:panel.runtime.status().state=='connected')
    js('(()=>{window.qaBase=32;window.qaStart=performance.now();window.qaFeed=()=>BeatlightPixel.receive({version:1,at:100,active:true,audible:true,kick:null,clock:{beat:qaBase+(performance.now()-qaStart)/1000*128/60,bpm:128,source:"link"},music:{state:"groove",energy:.65,tension:.1,brightness:.4,drop_id:0,drop_kicks:0,bass:0,density:0,activity:0}});BeatlightPixel.setInput("live");BeatlightPixel.arm(true);qaFeed();window.qaTimer=setInterval(qaFeed,40);return true;})()')
    pump(lambda:panel.enable.isEnabled());panel.enable.click();frames(4);panel.fold.setChecked(False)
    before=js('BeatlightPixel.status().performance')
    for mode in ('liquid','crossflow','chromatide'):
        js('(()=>{document.querySelector(\'#modeButtons button[data-mode="'+mode+'"]\').click();qaBase+=8;qaFeed();return true;})()')
        first=frames(4);last=frames(18);pixels=[last[p:p+3] for p in range(0,900,3)]
        levels=[max(pixel) for pixel in pixels]
        assert len(last)==900 and min(levels)>0
        assert len({max(range(3),key=lambda k:pixel[k]) for pixel in pixels})>=2
        assert max(levels)>min(levels)*1.4
        assert digest(first)!=digest(last)
        report['patterns'].append(dict(effect=mode,first_sha256=digest(first),last_sha256=digest(last),
            darkest_pixel=max(0,min(levels)),brightest_pixel=max(levels),flow=js('BeatlightPixel.status().flow')))
        for _ in range(6):app.processEvents();sleep(.01)
        assert window.grab().save(str(root/f'preview-organico-{mode}-v0.34.png'))
    control('flowDepth',0);flat=frames(4)
    assert len({tuple(flat[p:p+3]) for p in range(0,900,3)})==1
    control('flowDepth',65)
    phase=js('BeatlightPixel.status().flow.phase');control('flowSpeed',250)
    after_speed=js('BeatlightPixel.status().flow')
    assert phase<=after_speed['phase']<phase+1
    frames(16);assert js('BeatlightPixel.status().flow.effectiveSpeed')>2
    report['speed_no_phase_reset']=True
    control('flowSpeed',150);frames(10)
    after=js('BeatlightPixel.status().performance')
    assert after['allocations']==before['allocations'] and after['rootAllocations']==before['rootAllocations']
    report['buffers_reused']=True
    phase=js('BeatlightPixel.status().flow.phase');window.showMinimized();frames(12)
    assert js('BeatlightPixel.status().flow.phase')>phase
    report['minimized_motion_continues']=True
    window.showNormal();js('(BeatlightPixel.blackout(true),true)');pump(lambda:not any(device.frames[-1]))
    report.update(blackout_zero=True,frames=panel.runtime.status().frames,fps=panel.runtime.status().fps,
        render=js('BeatlightPixel.status().render_ms'))
    js('(clearInterval(qaTimer),true)')
finally:
    window.timer.start();window.close();pump(lambda:window.closed_ready)
assert device.closed and device.commands[-1].kind==BLACKOUT
saved=window.pixel_page.bridge.store.load()
assert saved['show']['flowDepth']==.65 and saved['show']['flowSpeed']==1.5
assert saved['patch']==project['patch']
report.update(persisted_controls=True,closed_cleanly=True,passed=True)
(root/'docs'/f'resultado-pixel-flow-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
