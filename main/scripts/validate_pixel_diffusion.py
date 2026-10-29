"""Mede o halo real no Canvas Qt, mantendo os mesmos pixels RGB congelados."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu --disable-gpu-compositing --no-sandbox')
os.environ.setdefault('QT_QUICK_BACKEND','software')
os.environ.setdefault('QT_OPENGL','software')
import json
from pathlib import Path
from time import monotonic,sleep
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.pixel.project import PixelProjectStore
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE
from beatlight import __version__

root=Path(__file__).resolve().parents[1];directory=root/'.runtime/pixel-diffusion-qa'
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

def settle(seconds=.4):
    until=monotonic()+seconds;pump(lambda:monotonic()>=until,seconds+2)

def js(expression):
    found={};window.pixel_page.webpage.runJavaScript('JSON.stringify('+expression+')',lambda value:found.update(value=value))
    pump(lambda:'value' in found);assert found['value'],expression
    return json.loads(found['value'])

metrics="""(()=>{const c=document.getElementById('stage'),w=c.width,h=c.height;
const data=c.getContext('2d').getImageData(0,0,w,h).data,s=w/1200,cx=Math.round(600*s);
let halo=0,far=0;for(let y=Math.round(170*s);y<Math.round(400*s);y++)for(let x=cx-40;x<=cx+40;x++){
const distance=Math.abs(x-cx),i=(y*w+x)*4,sum=data[i]+data[i+1]+data[i+2];
if(distance>4)halo+=sum;if(distance>=16)far+=sum;}
const core=(Math.round(280*s)*w+cx)*4;
const edge=[];for(let dx=4;dx<=35;dx++){const i=core+dx*4;edge.push(data[i]+data[i+1]+data[i+2]);}
return {halo,far,core:Array.from(data.slice(core,core+3)),edge};})()"""
report={'physical_device_used':False,'audio_capture_started':False,'samples':[]}
try:
    pump(lambda:window.pixel_page.bridge.ready_state and not window.busy);window.timer.stop()
    project=json.loads((root/'examples/ws2812-300.json').read_text(encoding='utf-8'))
    project['geometry']['lines'][0].update(start={'x':600,'y':80},end={'x':600,'y':480})
    project['show'].update(mode='ambient',brightness=1,followStructure=False,colorBehavior='solid',solidColor=[40,220,140],
        colorMode='rgb',white=0,kickMode='off',peakMode='off',strobes=False,glow=1)
    js('BeatlightPixel.applyProject('+json.dumps(project)+')')
    js('(BeatlightPixel.setInput("demo"),BeatlightPixel.arm(true),document.getElementById("playBtn").click(),true)')
    original=js('BeatlightPixel.renderFrame().strips[0].data')
    for value in (0,100,300):
        js(f'(document.getElementById("glow").value="{value}",document.getElementById("glow").dispatchEvent(new Event("input",{{bubbles:true}})),true)')
        settle();sample=js(metrics);sample['percent']=value;report['samples'].append(sample)
        assert js('BeatlightPixel.renderFrame().strips[0].data')==original
        window.grab().save(str(root/f'preview-pixel-diffusion-{value}.png'))
    zero,normal,maximum=report['samples']
    assert zero['halo']==0 and normal['halo']>0 and maximum['halo']>normal['halo'],report
    assert maximum['far']>normal['far'],report
    edge=maximum['edge'];first_zero=next((i for i,value in enumerate(edge) if value==0),len(edge))
    assert all(value==0 for value in edge[first_zero:]),'O halo não pode reaparecer em faixas separadas'
    assert zero['core']==normal['core']==maximum['core'] and max(zero['core'])>0,report
    report['rgb_unchanged']=True;report['zero_halo']=True;report['stronger_wider_halo']=True
    # A temporary virtual scene must not replace the original saved installation.
    js('(BeatlightPixel.enterSimulation(6),true)')
    js('(document.getElementById("glow").value="50",document.getElementById("glow").dispatchEvent(new Event("input",{bubbles:true})),true)')
finally:
    window.close();pump(lambda:window.closed_ready)
report['saved_glow']=PixelProjectStore(directory/'pixel-studio.json').load()['show']['glow']
assert report['saved_glow']==3
assert len(PixelProjectStore(directory/'pixel-studio.json').load()['geometry']['lines'])==1
report['original_project_preserved_after_virtual_preview']=True
report['closed_cleanly']=True;report['passed']=True
(root/'docs'/f'resultado-pixel-diffusion-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
