"""Mede palco, controles, apresentação leve e minimização com USB EMULADO."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu --disable-gpu-compositing --no-sandbox')
os.environ.setdefault('QT_QUICK_BACKEND','software')
os.environ.setdefault('QT_OPENGL','software')
import argparse
from collections import deque
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
from time import monotonic,sleep
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from beatlight import __version__
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.pixel.project import PixelProjectStore
from beatlight.pixel.usb import PixelUsbOutput
from beatlight.pixel.usb_protocol import OutputConfig
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE
import beatlight.ui.window as window_module

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--phase-seconds',type=float,default=8)
args=parser.parse_args()
if not 3<=args.phase_seconds<=60:parser.error('Use 3–60 segundos por fase.')
root=Path(__file__).resolve().parents[1];directory=root/'.runtime/pixel-presentation-qa'
sys.path.insert(0,str(root/'tests'))
from pixel_usb_fake import FakeEsp32Port

def cpu_seconds(pid):
    if os.name!='nt' or not pid:return None
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    kernel.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
    handle=kernel.OpenProcess(0x1000,False,int(pid))
    if not handle:return None
    try:
        creation,exit_time,kernel_time,user_time=(wintypes.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(handle,ctypes.byref(creation),ctypes.byref(exit_time),ctypes.byref(kernel_time),ctypes.byref(user_time)):return None
        return sum((value.dwHighDateTime<<32)|value.dwLowDateTime for value in (kernel_time,user_time))/10_000_000
    finally:kernel.CloseHandle(handle)

app=QApplication([]);app.setStyle('Fusion');app.setStyleSheet(STYLE)
if os.name=='nt':
    for name in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
project=json.loads((root/'examples/uma-fita-300-6-barras.json').read_text(encoding='utf-8'))
for group in project['patch']['mirrors']:group['mode']='exact'
PixelProjectStore(directory/'pixel-studio.json').save(project)
window=MainWindow(SettingsStore(directory/'preferences.json'),Settings(source='synthetic'))
panel=window.pixel_page.usb;device=FakeEsp32Port();device.frames=deque(maxlen=64);device.commands=deque(maxlen=128)
panel.runtime=PixelUsbOutput(lambda name:device)
window.show();window._navigate(9)
calls={'spectrum':0,'lighting':0,'stage':0}
for name,key in [('update_spectral_view','spectrum'),('update_lighting_view','lighting'),('update_stage_view','stage')]:
    original=getattr(window_module,name)
    def counted(*args,_original=original,_key=key,**kwargs):calls[_key]+=1;return _original(*args,**kwargs)
    setattr(window_module,name,counted)

def pump(condition,timeout=15):
    until=monotonic()+timeout
    while monotonic()<until:
        app.processEvents()
        if condition():return
        sleep(.003)
    assert condition(),window.pixel_page.notice.text()+' / '+panel.error

def settle(seconds):
    until=monotonic()+seconds;pump(lambda:monotonic()>=until,seconds+3)

def js(expression):
    found={};window.pixel_page.webpage.runJavaScript('JSON.stringify('+expression+')',lambda value:found.update(value=value))
    pump(lambda:'value' in found);assert found['value'],expression
    return json.loads(found['value'])

def status():return js('BeatlightPixel.status()')

report={'version':__version__,'physical_device_used':False,'serial_emulated_only':True,'phases':[]}
try:
    pump(lambda:window.pixel_page.bridge.ready_state and not window.busy and bool(window.devices))
    assert panel.preview_only and panel.runtime.closed and not device.frames
    before=js('BeatlightPixel.project()');js('(BeatlightPixel.previewProject(),true)');settle(.3)
    assert js('BeatlightPixel.project().geometry')==before['geometry']
    assert js('BeatlightPixel.project().patch')==before['patch']
    assert panel.runtime.closed and not device.frames
    report['project_preview_without_serial']=True
    js('(BeatlightPixel.setWorkspace("layout"),document.getElementById("connectionsFold").scrollIntoView({block:"start"}),true)')
    settle(.3);window.grab().save(str(root/'preview-pixel-groups-v0.26.png'))
    panel.mode.setCurrentIndex(1);settle(.2)
    js('(BeatlightPixel.setInput("live"),BeatlightPixel.arm(true),BeatlightPixel.setWorkspace("stage"),scrollTo(0,0),true)')
    window.source_combo.setCurrentIndex(window.source_combo.findData('synthetic'));window._start()
    pump(lambda:not window.busy and window.runtime.status().state=='running')
    panel.runtime.connect('FAKE-COM',OutputConfig());pump(lambda:panel.runtime.status().state=='connected')
    panel.last_sources=-10;panel._tick();pump(lambda:panel.source.count()==1)
    panel._arm(True);pump(lambda:bool(device.frames));settle(1)
    renderer_pid=window.pixel_page.webpage.renderProcessPid()
    phases=[('palco',9,False,False,'stage'),('controles',9,False,False,'effects'),
        ('leve',9,True,False,'stage'),('minimizado',9,False,True,'stage'),
        ('espectro_visivel',3,False,False,'stage'),('palco_PAR',7,False,False,'stage'),
        ('retorno_pixel',9,False,False,'stage')]
    for name,page,light,minimized,workspace in phases:
        window.showNormal();window._navigate(page);window.performance_button.setChecked(light)
        js('(BeatlightPixel.setWorkspace('+json.dumps(workspace)+'),true)')
        if minimized:window.showMinimized()
        window._tick();settle(.4)
        initial=status();start=monotonic();audio0=window.runtime.status().blocks;usb0=panel.runtime.status().frames
        render0=initial['render_ms']['frames'];legacy0=window.light_runtime.snapshot().frame_id;calls0=dict(calls)
        main0=cpu_seconds(os.getpid());renderer0=cpu_seconds(renderer_pid)
        pixels0=js('BeatlightPixel.renderFrame().strips[0].data')
        settle(args.phase_seconds)
        final=status();elapsed=monotonic()-start;main1=cpu_seconds(os.getpid());renderer1=cpu_seconds(renderer_pid)
        audio=window.runtime.status();usb=panel.runtime.status()
        pixels1=js('BeatlightPixel.renderFrame().strips[0].data')
        row={'name':name,'wall_seconds':round(elapsed,2),'main_cpu_core_percent':round((main1-main0)/elapsed*100,2) if main0 is not None else None,
          'renderer_cpu_core_percent':round((renderer1-renderer0)/elapsed*100,2) if renderer0 is not None else None,
          'canvas_frames':final['render_ms']['frames']-render0,'audio_blocks':audio.blocks-audio0,'dropped_audio_blocks':audio.dropped_blocks,
          'usb_frames':usb.frames-usb0,'legacy_frames':window.light_runtime.snapshot().frame_id-legacy0,
          'ui_updates':{key:calls[key]-calls0[key] for key in calls},'moving_pixels':pixels1!=pixels0,'musical_beats':final['beat']-initial['beat'],
          'has_lit_pixels':any(pixels0) or any(pixels1),'distinct_usb_frames':len(set(device.frames))}
        assert row['audio_blocks']>0 and row['usb_frames']>0 and usb.armed,row
        assert audio.dropped_blocks==0 and not window.pixel_page.render_errors,row
        assert row['has_lit_pixels'] and row['distinct_usb_frames']>1 and row['musical_beats']>0,row
        if name not in ('palco','retorno_pixel'):assert row['canvas_frames']==0,row
        else:assert row['canvas_frames']>0,row
        assert row['ui_updates']['spectrum']>0 if page==3 else row['ui_updates']['spectrum']==0,row
        if page!=7:assert row['legacy_frames']==0 and row['ui_updates']['lighting']==0,row
        else:assert row['legacy_frames']>0,row
        assert js('(()=>{const s=BeatlightPixel.renderFrame().strips;return s[0].data.every((v,i)=>v===s[5].data[i])&&s[1].data.every((v,i)=>v===s[4].data[i])&&s[2].data.every((v,i)=>v===s[3].data[i])})()')
        report['phases'].append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    window.showNormal();window._navigate(9);window.performance_button.setChecked(True);settle(.3)
    window.grab().save(str(root/'preview-pixel-presentation-v0.26.png'))
    js('(BeatlightPixel.previewProject(),true)');pump(lambda:panel.preview_only and panel.runtime.closed)
    frame_count=len(device.frames);settle(.5);assert len(device.frames)==frame_count
    report['switch_to_preview_disarms_and_disconnects']=True
finally:
    window.close();pump(lambda:window.closed_ready,20)
report['passed']=True
(root/'docs'/f'resultado-pixel-presentation-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('APROVADO · prévia, grupos, páginas ocultas, minimização e apresentação leve.',flush=True)
