"""Saída do contínuo fixo e participação ocasional no AUTO, em Qt/USB emulado."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu --disable-gpu-compositing --no-sandbox')
os.environ.setdefault('QT_QUICK_BACKEND','software')
os.environ.setdefault('QT_OPENGL','software')
from collections import deque
import json,sys
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
window=MainWindow(SettingsStore(root/'.runtime/auto-continuous/preferences.json'),Settings(source='synthetic'))
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
def click(button):return js('(document.getElementById('+json.dumps(button)+').click(),true)')
def seek(beat):return js('(qaBeat='+json.dumps(beat)+',qaFeed(),true)')
def screenshot(name):
    for _ in range(8):app.processEvents();sleep(.01)
    assert window.grab().save(str(root/name))
report=dict(version=__version__,physical_device_used=False,emulated_serial=True,choices=[])
try:
    pump(lambda:window.pixel_page.bridge.ready_state and not window.busy)
    window.timer.stop();panel.mode.setCurrentIndex(1)
    project=json.loads((root/'examples/uma-fita-300-6-barras.json').read_text(encoding='utf-8'))
    project['show'].update(mode='auto',compositionStyle='hypnotic',autoContinuous=True,changeMode='bars',sceneBars=1,morphBeats=4,peakMode='off',strobes=False)
    for strip in project['strips']:strip.update(effect='inherit',palette='inherit',response='hybrid')
    js('BeatlightPixel.applyProject('+json.dumps(project)+')')
    pump(lambda:panel.source.count()==1 and panel.connect_button.isEnabled())
    panel.port.clear();panel.port.addItem('EMULADO · sem placa física','EMULATED')
    panel.connect_button.click();pump(lambda:panel.runtime.status().state=='connected')
    js('(()=>{window.qaBeat=32;window.qaFeed=()=>BeatlightPixel.receive({version:1,at:100,active:true,audible:true,kick:null,clock:{beat:qaBeat,bpm:128,source:"link"},music:{state:"groove",energy:.65,tension:.15,brightness:.4,drop_id:0,drop_kicks:0,bass:.6,density:.6,activity:.4}});BeatlightPixel.setInput("live");BeatlightPixel.arm(true);qaFeed();window.qaTimer=setInterval(qaFeed,30);return true;})()')
    pump(lambda:panel.enable.isEnabled());panel.enable.click();frames();panel.fold.setChecked(False)
    before=js('BeatlightPixel.status().performance')
    click('quickContinuous');assert js('BeatlightPixel.status().continuous.fixed')
    seek(40);frames();screenshot('preview-continuo-fixo-v0.35.png')
    click('quickAuto');assert not js('BeatlightPixel.status().continuous.fixed')
    assert not js('BeatlightPixel.status().continuous.automatic')
    assert js('BeatlightPixel.project().show.compositionStyle')=='hypnotic'
    seek(48);frames();screenshot('preview-auto-retomado-v0.35.png')
    click('quickContinuous');click('quickOrganic');assert not js('BeatlightPixel.status().continuous.fixed')
    assert js('BeatlightPixel.status().effect')=='organic'
    click('quickContinuous');click('quickContinuous');assert js('BeatlightPixel.status().effect')=='auto'
    assert not js('BeatlightPixel.status().continuous.fixed')
    report['exit_buttons_work']=True
    click('quickAuto');seen=0
    for i in range(18):
        state=js('BeatlightPixel.status()');c=state['continuous']
        assert state['effect']=='auto' and not c['fixed']
        report['choices'].append(dict(beat=state['beat'],continuous=c['automatic'],family=state['family'],minimum=state['minimumBeats']))
        if c['automatic']:
            assert not report['choices'][-2]['continuous']
            assert state['minimumBeats']==32
            seek(state['beat']+8);payload=frames()
            assert all(max(payload[p:p+3])>0 for p in range(0,900,3))
            assert js('document.getElementById("quickAuto").getAttribute("aria-pressed")')=='true'
            assert js('document.getElementById("quickContinuous").getAttribute("aria-pressed")')=='false'
            if not seen:screenshot('preview-auto-continuo-ocasional-v0.35.png')
            seen+=1
        seek(state['nextBeat']);frames(2)
    assert seen>=3
    after=js('BeatlightPixel.status().performance')
    assert after['allocations']==before['allocations'] and after['rootAllocations']==before['rootAllocations']
    report.update(continuous_entries=seen,buffers_reused=True)
    js('(()=>{const e=document.getElementById("autoContinuous");e.value="no";e.dispatchEvent(new Event("change"));return true;})()')
    assert not js('BeatlightPixel.project().show.autoContinuous')
    assert not js('BeatlightPixel.status().continuous.automatic')
    window.showMinimized();frames(8);report['minimized_output_continues']=True
    window.showNormal();js('(BeatlightPixel.blackout(true),true)');pump(lambda:not any(device.frames[-1]))
    report.update(blackout_zero=True,frames=panel.runtime.status().frames,fps=panel.runtime.status().fps)
    js('(clearInterval(qaTimer),true)')
finally:
    window.timer.start();window.close();pump(lambda:window.closed_ready)
assert device.closed and device.commands[-1].kind==BLACKOUT
saved=window.pixel_page.bridge.store.load()
assert saved['show']['autoContinuous'] is False and saved['show']['compositionStyle']=='hypnotic'
assert saved['patch']==project['patch']
report.update(persisted_controls=True,closed_cleanly=True,passed=True)
(root/'docs'/f'resultado-auto-continuous-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
