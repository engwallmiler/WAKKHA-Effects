"""Direção visual em Qt e USB emulado, sem áudio/COM físicos."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu --disable-gpu-compositing --no-sandbox')
os.environ.setdefault('QT_QUICK_BACKEND','software')
os.environ.setdefault('QT_OPENGL','software')
from collections import deque
import hashlib
import json
from pathlib import Path
import sys
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
window=MainWindow(SettingsStore(root/'.runtime/pixel-direction/preferences.json'),Settings(source='synthetic'))
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
    pump(lambda:bool(result));assert result[0]
    return json.loads(result[0])
report={'version':__version__,'physical_device_used':False,'emulated_serial':True,'drops':[],'contexts':[]}
try:
    pump(lambda:window.pixel_page.bridge.ready_state and not window.busy)
    panel.mode.setCurrentIndex(1)
    project=json.loads((root/'examples/uma-fita-300-6-barras.json').read_text(encoding='utf-8'))
    project['show'].update(mode='auto',changeMode='hold',musicColors=True,dropVariety=True,strobes=False)
    js('BeatlightPixel.applyProject('+json.dumps(project)+')')
    pump(lambda:panel.source.count()==1 and panel.connect_button.isEnabled())
    panel.port.clear();panel.port.addItem('EMULADO · sem placa física','EMULATED')
    panel.connect_button.click();pump(lambda:panel.runtime.status().state=='connected')
    js('(BeatlightPixel.setInput("demo"),BeatlightPixel.arm(true),true)')
    pump(lambda:panel.enable.isEnabled());panel.enable.click();pump(lambda:panel.runtime.status().frames>=5)
    panel.fold.setChecked(False)
    before=js('BeatlightPixel.status().performance')
    for index in range(12):
        js('BeatlightPixel.manualDrop()');status=js('BeatlightPixel.status()')
        count=panel.runtime.status().frames;pump(lambda:panel.runtime.status().frames>=count+10)
        payload=device.frames[-1];assert len(payload)==900 and any(payload)
        report['drops'].append({'motif':status['dropMotif'],'name':status['dropName'],'palette':status['colours']['primary'],
            'frame_sha256':hashlib.sha256(payload).hexdigest(),'fps':panel.runtime.status().fps})
        if index<3:
            for _ in range(10):app.processEvents();sleep(.01)
            assert window.grab().save(str(root/f'preview-drop-variant-{index+1}-v0.30.png'))
        js('BeatlightPixel.manualDrop()')
    assert len({item['motif'] for item in report['drops']})==12
    assert len({item['frame_sha256'] for item in report['drops']})==12
    after=js('BeatlightPixel.status().performance')
    assert after['allocations']==before['allocations'] and after['rootAllocations']==before['rootAllocations']
    report['buffers_reused']=True

    # Rótulos sintéticos alimentam somente esta sessão de QA; a captura não abre.
    window.timer.stop()
    js('(()=>{window.qaMusic={state:"groove",energy:.65,tension:.2,drop_id:0,drop_kicks:0};window.qaStart=performance.now();window.qaFeed=()=>{let beat=32+(performance.now()-qaStart)/1000*128/60;BeatlightPixel.receive({version:1,at:100,active:true,audible:true,kick:{id:Math.floor(beat),strength:.9,age:(beat%1)*60/128},clock:{beat,bpm:128,source:"link"},music:{brightness:.5,bass:.6,density:.6,activity:.4,...qaMusic}});};BeatlightPixel.setInput("live");window.qaTimer=setInterval(qaFeed,50);qaFeed();return true;})()')
    for cycle in range(2):
        for context,energy,tension in [('breakdown',.12,.05),('buildup',.7,.9),('groove',.85,.15)]:
            js('Object.assign(qaMusic,'+json.dumps({'state':context,'energy':energy,'tension':tension})+')')
            pump(lambda:js('BeatlightPixel.status().context')==context)
            count=panel.runtime.status().frames;pump(lambda:panel.runtime.status().frames>=count+8)
            state=js('BeatlightPixel.status()');report['contexts'].append({key:state[key] for key in ('context','family','signature','colours')})
    for context in ('breakdown','buildup','groove'):
        entries=[item for item in report['contexts'] if item['context']==context]
        assert entries[0]['signature']!=entries[1]['signature']
        assert entries[0]['colours']['primary']!=entries[1]['colours']['primary']
    js('(Object.assign(qaMusic,{state:"groove"}),clearInterval(qaTimer),true)')
    before_hidden=panel.runtime.status().frames;window.showMinimized()
    js('(BeatlightPixel.setInput("demo"),true)')
    pump(lambda:panel.runtime.status().frames>=before_hidden+8)
    report['minimized_output_continues']=True
    window.showNormal();window._navigate(9)
    js('(BeatlightPixel.blackout(true),true)');pump(lambda:not any(device.frames[-1]));report['blackout_zero']=True
    report.update(frames=panel.runtime.status().frames,fps=panel.runtime.status().fps,performance=js('BeatlightPixel.status().performance'))
finally:
    window.timer.start();window.close();pump(lambda:window.closed_ready)
assert device.closed and device.commands[-1].kind==BLACKOUT
report.update(closed_cleanly=True,passed=True)
(root/'docs'/f'resultado-pixel-direction-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
