"""Ensaio nativo, sem hardware: relógio acelerado, áudio real sintético e USB emulado.

--seconds 21600 --music-hours 6 executa seis horas reais. O padrão é curto e
acelera somente o relógio musical; não equivale a seis horas reais de operação.
"""
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
from time import monotonic,process_time,sleep
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import QTimer
from beatlight import __version__
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.pixel.project import PixelProjectStore
from beatlight.pixel.usb import PixelUsbOutput
from beatlight.pixel.usb_protocol import OutputConfig,BLACKOUT
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--seconds',type=float,default=60)
parser.add_argument('--music-hours',type=float,default=8)
args=parser.parse_args()
if not 10<=args.seconds<=43200 or not 1<=args.music_hours<=24:parser.error('Use 10–43200 segundos reais e 1–24 horas musicais.')
root=Path(__file__).resolve().parents[1];directory=root/'.runtime/pixel-endurance-qa'
sys.path.insert(0,str(root/'tests'))
from pixel_usb_fake import FakeEsp32Port

class MemoryCounters(ctypes.Structure):
    _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in
      ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]

def rss(pid):
    if os.name!='nt' or not pid:return None
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);psapi=ctypes.WinDLL('psapi',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE];psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(MemoryCounters),wintypes.DWORD]
    handle=kernel.OpenProcess(0x410,False,int(pid))
    if not handle:return None
    try:
        counters=MemoryCounters();counters.cb=ctypes.sizeof(counters)
        return counters.WorkingSetSize if psapi.GetProcessMemoryInfo(handle,ctypes.byref(counters),counters.cb) else None
    finally:kernel.CloseHandle(handle)

app=QApplication([]);app.setStyle('Fusion');app.setStyleSheet(STYLE)
if os.name=='nt':
    for name in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
store=PixelProjectStore(directory/'pixel-studio.json')
example=json.loads((root/'examples/uma-fita-300-6-barras.json').read_text(encoding='utf-8'));store.save(example)
expected_sources=len(example['patch']['runs'])+len(example['strips'])-sum(len(run['segments']) for run in example['patch']['runs'])
window=MainWindow(SettingsStore(directory/'preferences.json'),Settings(source='synthetic'))
device=FakeEsp32Port();panel=window.pixel_page.usb;panel.runtime=PixelUsbOutput(lambda name:device)
device.frames=deque(maxlen=64);device.commands=deque(maxlen=128)
window.show();window._navigate(9)

def pump(condition,timeout=15):
    until=monotonic()+timeout
    while monotonic()<until:
        app.processEvents()
        if condition():return
        sleep(.003)
    assert condition(),window.pixel_page.notice.text()+' / '+panel.error

def settle(seconds):
    until=monotonic()+seconds;pump(lambda:monotonic()>=until,seconds+2)

def js(expression):
    found={};window.pixel_page.webpage.runJavaScript('JSON.stringify('+expression+')',lambda value:found.update(value=value))
    pump(lambda:'value' in found);assert found['value'],expression
    return json.loads(found['value'])

def status():return js('BeatlightPixel.status()')

samples=deque(maxlen=256);started=None;drop_id=0;published=0;feed=QTimer();feed.setInterval(40)
def publish():
    global published,drop_id
    if started is None:return
    at=monotonic();elapsed=at-started;published+=1;cycle=int(elapsed/12);position=elapsed%12
    context='groove' if position<7 else 'breakdown' if position<9 else 'buildup' if position<11 else 'drop'
    count=min(8,1+int((position-11)*8)) if context=='drop' else 0
    energy=.15 if context=='breakdown' else .9 if context=='drop' else .7
    packet={'version':1,'at':at,'sent_at':at,'active':True,'audible':True,
      'clock':{'beat':32+min(1,elapsed/args.seconds)*args.music_hours*7200,'bpm':120,'source':'link'},
      'kick':{'id':at,'age':0,'strength':1} if context=='drop' else None,
      'music':{'state':context,'energy':energy,'tension':.95 if context=='buildup' else .1,'brightness':.4,
        'bass':.65,'density':.5,'activity':.4,'drop_id':cycle+1 if context=='drop' else cycle,
        'drop_kicks':count,'drop_phase':'confirmed' if count>=3 else 'impact' if count else 'idle'}}
    window.pixel_page.bridge.send_music(packet)
feed.timeout.connect(publish)

report={'version':__version__,'physical_device_used':False,'serial_emulated_only':True,
  'requested_wall_seconds':args.seconds,'requested_musical_hours':args.music_hours,'real_six_hour_run':args.seconds>=21600}
try:
    pump(lambda:window.pixel_page.bridge.ready_state and not window.busy and bool(window.devices))
    panel.mode.setCurrentIndex(1)
    window.timer.stop();js('(BeatlightPixel.setInput("demo"),BeatlightPixel.arm(true),true)')
    settle(.5)
    # Check the actual controls and make a reviewable image before starting audio.
    js('(document.getElementById("presentationBtn").click(),document.getElementById("geometryFold").open=true,document.getElementById("connectionsFold").open=true,document.getElementById("runSelect").value='+json.dumps(example['patch']['runs'][0]['id'])+',document.getElementById("runSelect").dispatchEvent(new Event("change")),document.getElementById("connectionsFold").scrollIntoView({block:"center"}),true)')
    settle(.5);window.grab().save(str(root/'preview-pixel-connections.png'))
    js('(document.getElementById("presentationBtn").click(),document.getElementById("stage").scrollIntoView({block:"center"}),true)')
    # Force 50 ms disk writes in the worker, never in the GUI thread.
    save=store.save
    def slow_save(data):sleep(.05);save(data)
    window.pixel_page.bridge.writer.store.save=slow_save
    window.source_combo.setCurrentIndex(window.source_combo.findData('synthetic'));window._start()
    pump(lambda:not window.busy and window.runtime.status().state=='running')
    panel.runtime.connect('FAKE-COM',OutputConfig());pump(lambda:panel.runtime.status().state=='connected')
    panel.last_sources=-10;panel._tick();pump(lambda:panel.source.count()==expected_sources)
    js('(BeatlightPixel.setInput("live"),BeatlightPixel.arm(true),true)')
    initial=status()['performance'];started=monotonic();cpu_start=process_time();feed.start();publish();settle(.1)
    panel._arm(True);pump(lambda:bool(device.frames));freeze_at=None;checked=False;last_sample=-10;last_edit=-10;render_peak=0;renderer_pid=0;previous_render=-1
    while monotonic()-started<args.seconds:
        app.processEvents();sleep(.003);elapsed=monotonic()-started
        if elapsed-last_edit>=2:
            last_edit=elapsed;value=146+int(elapsed)%8
            js(f'(document.getElementById("lineStartX").value="{value}",document.getElementById("lineForm").dispatchEvent(new Event("submit",{{cancelable:true}})),true)')
        if freeze_at is None and elapsed>=args.seconds/2:
            freeze_at=elapsed
            window.pixel_page.webpage.runJavaScript('(()=>{const until=performance.now()+450;while(performance.now()<until){};return true})()')
        if freeze_at is not None and not checked and elapsed-freeze_at>1:
            assert not panel.runtime.status().armed and device.commands[-1].kind==BLACKOUT
            report['renderer_stall_disarms_output']=True;report['stale_frames_rejected']=True
            panel._arm(True);checked=True
        if elapsed-last_sample>=max(2,args.seconds/20):
            last_sample=elapsed;s=status();p=s['performance'];render_peak=max(render_peak,s['render_ms']['max'])
            assert s['render_ms']['frames']>previous_render;previous_render=s['render_ms']['frames']
            assert not window.pixel_page.render_errors,list(window.pixel_page.render_errors)
            assert p['allocations']==initial['allocations'] and p['rootAllocations']==initial['rootAllocations'],(initial,p)
            assert p['signal_bytes']==initial['signal_bytes'] and p['history']<=12
            assert window.pixel_page.bridge.writer.pending<=1
            assert js('(()=>{const s=BeatlightPixel.renderFrame().strips;return s.every(s=>s.data.every(v=>Number.isInteger(v)&&v>=0&&v<=255))&&s[0].data.every((v,i)=>v===s[5].data[i])&&s[1].data.every((v,i)=>v===s[4].data[i])&&s[2].data.every((v,i)=>v===s[3].data[i])})()')
            renderer_pid=getattr(window.pixel_page.webpage,'renderProcessPid',lambda:0)()
            heap=js('(performance.memory?{used:performance.memory.usedJSHeapSize,total:performance.memory.totalJSHeapSize}:null)')
            samples.append({'wall_seconds':round(elapsed,2),'musical_beat':s['beat'],'main_rss':rss(os.getpid()),'renderer_rss':rss(renderer_pid),'js_heap':heap,
              'history':p['history'],'texture_bytes':p['texture_bytes'],'signal_bytes':p['signal_bytes'],'render_average_ms':s['render_ms']['average']})
    publish();pump(lambda:status()['beat']>=32+args.music_hours*7200)
    final=status();audio=window.runtime.status();report.update(actual_wall_seconds=monotonic()-started,
      main_cpu_seconds=process_time()-cpu_start,published_packets=published,musical_hours_observed=(final['beat']-32)/7200,
      musical_coalesced=window.pixel_page.bridge.music_coalesced,render_ms=final['render_ms'],performance=final['performance'],
      audio_blocks=audio.total_blocks if hasattr(audio,'total_blocks') else audio.blocks,dropped_audio_blocks=audio.dropped_blocks,
      usb_frames=panel.runtime.status().frames,usb_fps=panel.runtime.status().fps,project_writes=window.pixel_page.bridge.writer.writes,
      project_replacements=window.pixel_page.bridge.writer.replaced,renderer_pid=renderer_pid,
      stable_buffers=True,mirror_checks=True,samples=list(samples))
    assert checked and report['musical_coalesced']>0
    assert not window.pixel_page.bridge.writer.error
    assert report['dropped_audio_blocks']==0,report['dropped_audio_blocks']
    feed.stop();blocks_before=window.runtime.status().blocks;panel.reload.click()
    pump(lambda:window.pixel_page.bridge.ready_state and not window.pixel_page._reloading)
    assert not panel.runtime.status().armed and window.runtime.status().state=='running'
    assert js('BeatlightPixel.project().patch.runs.length')==len(example['patch']['runs'])
    pump(lambda:window.runtime.status().blocks>blocks_before)
    report['preview_reload_preserves_audio_and_project']=True
finally:
    feed.stop();window.close();pump(lambda:window.closed_ready,20)
report['closed_cleanly']=True;report['passed']=True
(root/'docs'/f'resultado-pixel-endurance-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({key:value for key,value in report.items() if key!='samples'},ensure_ascii=False,indent=2))
