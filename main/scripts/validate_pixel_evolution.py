"""Camadas, picos, estrutura e layout no renderer nativo, com relógio controlado."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu --disable-gpu-compositing --no-sandbox')
os.environ.setdefault('QT_QUICK_BACKEND','software')
os.environ.setdefault('QT_OPENGL','software')
from pathlib import Path
import json
from time import monotonic,sleep
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import QTimer
from beatlight import __version__
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.pixel.project import PixelProjectStore
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE

root=Path(__file__).resolve().parents[1]
directory=root/'.runtime/pixel-evolution-qa'
real=Path(os.environ.get('LOCALAPPDATA','C:/Users/walli/AppData/Local'))/'WAKKHA/BEATLIGHT DMX/pixel-studio.json'
original=PixelProjectStore(real).load() if real.exists() else None
if original:PixelProjectStore(directory/'pixel-studio.json').save(original)
app=QApplication([]);app.setStyle('Fusion');app.setStyleSheet(STYLE)
if os.name=='nt':
    for name in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
window=MainWindow(SettingsStore(directory/'preferences.json'),Settings(source='synthetic'))
window.show();window._navigate(9)

def pump(condition,timeout=15):
    until=monotonic()+timeout
    while monotonic()<until:
        app.processEvents()
        if condition():return
        sleep(.005)
    assert condition(),window.pixel_page.notice.text()

def js(expression):
    found={};window.pixel_page.webpage.runJavaScript('JSON.stringify('+expression+')',lambda value:found.update(value=value))
    pump(lambda:'value' in found);assert found['value'],window.pixel_page.notice.text()
    return json.loads(found['value'])

current=None;anchor=0
def publish():
    if current is None:return
    at=monotonic();packet={**current,'at':at,'sent_at':at,'clock':{**current['clock'],'beat':current['clock']['beat']+(at-anchor)*2}}
    window.pixel_page.bridge.packet.emit(json.dumps(packet))
feed=QTimer();feed.setInterval(40);feed.timeout.connect(publish)
def send(beat,context='groove',energy=.7,tension=.1,drop=0,count=0):
    global current,anchor
    at=monotonic();anchor=at
    current={'version':1,'at':at,'sent_at':at,'active':True,'audible':True,'clock':{'beat':beat,'bpm':120,'source':'link'},
        'kick':{'id':at,'age':0,'strength':1} if context=='drop' else None,
        'music':{'state':context,'energy':energy,'tension':tension,'brightness':.4,'bass':.65,'density':.7,'activity':.4,
                 'drop_id':drop,'drop_kicks':count,'drop_phase':'confirmed' if count>=3 else 'impact' if count else 'idle'}}
    publish();feed.start();pump(lambda:js('BeatlightPixel.status().structure')==context)
def status():return js('BeatlightPixel.status()')
def rect():return js("(()=>{const r=document.getElementById('stage').getBoundingClientRect();return {top:r.top,width:r.width,height:r.height,bottom:r.bottom,viewport:innerHeight}})()")

report={'physical_output':False,'actual_project_cloned':bool(original),'layers':[],'drop_plans':[]}
try:
    pump(lambda:window.pixel_page.bridge.ready_state and not window.busy)
    window.timer.stop()
    project=js('BeatlightPixel.project()');project['show'].update(mode='auto',sceneBars=1,changeMode='bars',compositionStyle='hypnotic',layerCount=4,progressive=True,peakMode='auto',energyMotion=True,followStructure=True,brightness=.65,palette='neon')
    for strip in project['strips']:strip.update(effect='inherit',response='hybrid')
    js('BeatlightPixel.applyProject('+json.dumps(project)+')');js('(BeatlightPixel.arm(true),true)')
    assert js('document.body.classList.contains("presentation")')
    assert not window.pixel_page.usb.controls_box.isVisible() and window.pixel_page.usb.off.isVisible()
    send(32);first=status()['composition_id'];deadline=status()['nextBeat'];initial=rect();first_family=status()['family'];first_layers=status()['layers']
    assert 64<=deadline<=68,deadline  # A native clock may enter just after a bar boundary.
    for beat in (32,40,48,63.8):
        send(beat);s=status();assert s['composition_id']==first
        report['layers'].append({'beat':beat,'weights':[layer['weight'] for layer in s['layers']]})
    send(deadline);assert status()['composition_id']!=first
    assert status()['family']==first_family
    assert len([layer for layer in status()['layers'] if not any(old['id']==layer['id'] for old in first_layers)])==1
    report['first_deadline']=deadline
    report['connected_family']=first_family
    assert initial['bottom']<=initial['viewport']+2,initial
    send(80,'breakdown',.08,.04);pump(lambda:status()['context']=='breakdown')
    pump(lambda:status()['motionFactor']<.4,3);report['calm_speed']=status()['motionFactor'];broken=status()['composition_id']
    calm_rect=rect()
    assert abs(calm_rect['top']-initial['top'])<2 and abs(calm_rect['height']-initial['height'])<2
    send(84,'buildup',.8,.95);pump(lambda:status()['context']=='buildup')
    pump(lambda:status()['motionFactor']>1.8,3);report['build_speed']=status()['motionFactor']
    assert status()['composition_id']!=broken
    js('(document.getElementById("peakSync").click(),true)');pump(lambda:js('BeatlightPixel.project().show.peakMode')=='on')
    report['peak_sync']=status()['peak']['every'] in (4,8)
    for drop,start in ((1,96),(2,112)):
        for count in range(1,9):
            send(start+count-1,'drop',.95,1,drop,count)
            if count==1:report['drop_plans'].append({'variant':status()['dropVariant'],'layers':status()['dropLayers']})
            assert status()['drop_kicks']==count and status()['effect']=='dropseq'
        send(start+8,'groove',drop=drop);assert status()['effect']=='auto'
    assert report['drop_plans'][0]['variant']!=report['drop_plans'][1]['variant']
    # Fold controls deliberately; musical updates must not change their state.
    js('(document.getElementById("presentationBtn").click(),document.getElementById("automationFold").open=true,true)')
    assert js('document.getElementById("automationFold").open')
    send(124);assert js('document.getElementById("automationFold").open')
    js('(document.getElementById("automationFold").open=false,document.getElementById("presentationBtn").click(),true)')
    send(128);pump(lambda:status()['transition']==0,6)
    pump(lambda:js('document.getElementById("peakRead").textContent.startsWith("GROOVE")'))
    assert js('document.body.classList.contains("presentation")')
    settle=monotonic()+.7;pump(lambda:monotonic()>=settle,2)
    window.grab().save(str(root/'preview-pixel-evolution.png'))
    report.update(lines=len(project['strips']),pixels=sum(line['pixels'] for line in project['geometry']['lines']),stable_stage=True,
        minimum_thirtytwo=True,one_layer_changes=True,folds=True,stage=rect(),completed=True)
finally:
    feed.stop();window.close();pump(lambda:window.closed_ready)
report['closed_cleanly']=window.closed_ready
(root/'docs'/f'resultado-pixel-evolution-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
