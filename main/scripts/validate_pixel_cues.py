"""Regressão da configuração do usuário, clonada, com relógio/estrutura controlados.

Não altera AppData e não inicia áudio ou Link nativo.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--no-sandbox')
os.environ.setdefault('QT_OPENGL','software')
import json
from pathlib import Path
from time import monotonic,sleep
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.pixel.project import PixelProjectStore
from beatlight.pixel.protocol import validate_frame
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE
from beatlight import __version__

root=Path(__file__).resolve().parents[1]
directory=root/'.runtime'/'pixel-cues-qa'
real=Path(os.environ.get('LOCALAPPDATA','C:/Users/walli/AppData/Local'))/'WAKKHA'/'BEATLIGHT DMX'/'pixel-studio.json'
original=PixelProjectStore(real).load() if real.exists() else None
if original:PixelProjectStore(directory/'pixel-studio.json').save(original)
app=QApplication([]);app.setStyle('Fusion');app.setStyleSheet(STYLE)
window=MainWindow(SettingsStore(directory/'preferences.json'),Settings(source='synthetic'))
window.show();window._navigate(9)

def pump(condition,timeout=15):
    end=monotonic()+timeout
    while monotonic()<end:
        app.processEvents()
        if condition():return
        sleep(.005)
    assert condition(),window.pixel_page.notice.text()

def js(expression):
    found={}
    window.pixel_page.webpage.runJavaScript('JSON.stringify('+expression+')',lambda data:found.update(data=data))
    pump(lambda:'data' in found)
    assert found['data'],window.pixel_page.notice.text()
    return json.loads(found['data'])

current_packet=None
anchor=0
def publish():
    if current_packet is None:return
    at=monotonic()
    packet={**current_packet,'at':at,'sent_at':at,'clock':{**current_packet['clock'],'beat':current_packet['clock']['beat']+(at-anchor)*2}}
    window.pixel_page.bridge.packet.emit(json.dumps(packet))

feed=QTimer();feed.setInterval(50);feed.timeout.connect(publish)
def send(beat,state='groove',drop=0,count=0):
    global current_packet,anchor
    packet={'version':1,'at':monotonic(),'active':True,'audible':True,
            'clock':{'beat':beat,'bpm':120,'source':'link'},'kick':None,
            'music':{'state':state,'energy':.3 if state=='breakdown' else .7,
                     'tension':.9 if state=='buildup' else .15,'brightness':.3,
                     'bass':.1 if state=='breakdown' else .6,'density':.4,'activity':.4,
                     'drop_id':drop,'drop_kicks':count}}
    current_packet=packet;anchor=monotonic();publish();feed.start()
    pump(lambda:js('BeatlightPixel.status().structure')==state)

report={'physical_output':False,'actual_project_cloned':bool(original),'patterns':[]}
try:
    pump(lambda:window.pixel_page.bridge.ready_state)
    window.timer.stop()
    project=js('BeatlightPixel.project()')
    assert project['show']['changeMode']=='hybrid' if original and 'changeMode' not in original['show'] else True
    report.update(lines=len(project['strips']),pixels=sum(line['pixels'] for line in project['geometry']['lines']))
    # A configuração observada do usuário é orgânica; o teste de cadência é
    # explícito para continuar útil se o próximo projeto salvo estiver manual.
    project['show'].update(mode='organic',changeMode='hybrid',sceneBars=4,followStructure=True)
    js('BeatlightPixel.applyProject('+json.dumps(project)+')')
    js('(BeatlightPixel.arm(true),true)')
    for beat in (32,48,64):
        send(beat)
        current=js('BeatlightPixel.status()')
        report['patterns'].append({'beat':beat,'pattern':current['pattern'],'next':current['nextBeat']})
    assert len({entry['pattern'] for entry in report['patterns']})==3
    assert all(entry['next']>entry['beat'] for entry in report['patterns'])
    send(68,'breakdown');pump(lambda:js('BeatlightPixel.status().context')=='breakdown',2)
    report['breakdown_pattern']=js('BeatlightPixel.status().pattern')
    send(72,'buildup');pump(lambda:js('BeatlightPixel.status().context')=='buildup',2)
    report['buildup_pattern']=js('BeatlightPixel.status().pattern')
    send(76.1,'drop',1,1);assert js('BeatlightPixel.status().effect')=='dropseq'
    validate_frame(js('BeatlightPixel.renderFrame()'))
    report['automatic_drop']=True
    js('(BeatlightPixel.manualDrop(),true)');assert js('BeatlightPixel.status().manualDrop')
    js('(BeatlightPixel.manualDrop(),true)');assert not js('BeatlightPixel.status().manualDrop')
    report['manual_drop']=True
    send(85,'groove',1)
    js('(BeatlightPixel.blackout(true),true)')
    assert all(not any(strip['data']) for strip in js('BeatlightPixel.renderFrame()')['strips'])
    report['blackout_zero']=True
    report['completed']=True
finally:
    feed.stop()
    window.close();pump(lambda:window.closed_ready)
report['closed_cleanly']=window.closed_ready
(root/'docs'/f'resultado-pixel-cues-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
