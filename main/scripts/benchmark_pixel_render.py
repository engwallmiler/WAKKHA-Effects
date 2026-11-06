"""Comparação repetível de prévia por software, sem áudio ou dispositivos físicos."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu --disable-gpu-compositing --no-sandbox')
import argparse,ctypes,json,tempfile
from zipfile import ZipFile
from pathlib import Path
from time import monotonic,sleep
from PySide6.QtWidgets import QApplication
from beatlight import __version__
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.ui.window import MainWindow
parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);parser.add_argument('--seconds',type=float,default=6);parser.add_argument('--reference-wheel',type=Path);parser.add_argument('--extended',action='store_true');parser.add_argument('--single',action='store_true')
args=parser.parse_args();root=Path(__file__).resolve().parents[1];app=QApplication([])
def cpu(pid):
    if os.name!='nt':return None
    from ctypes import wintypes as w
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
    kernel.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)]
    kernel.CloseHandle.argtypes=[w.HANDLE]
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return None
    times=[w.FILETIME() for _ in range(4)]
    try:
        if not kernel.GetProcessTimes(handle,*(ctypes.byref(t) for t in times)):return None
        return sum((t.dwHighDateTime<<32)|t.dwLowDateTime for t in times[2:])/1e7
    finally:kernel.CloseHandle(handle)
def memory(pid):
    if os.name!='nt':return None
    from ctypes import wintypes as w
    class Counters(ctypes.Structure):
        _fields_=[('cb',w.DWORD),('faults',w.DWORD)]+[(name,ctypes.c_size_t) for name in ('peak','working','quota_peak_paged','quota_paged','quota_peak_nonpaged','quota_nonpaged','pagefile','peak_pagefile','private')]
    kernel=ctypes.WinDLL('kernel32');api=ctypes.WinDLL('psapi')
    kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE;kernel.CloseHandle.argtypes=[w.HANDLE]
    api.GetProcessMemoryInfo.argtypes=[w.HANDLE,ctypes.POINTER(Counters),w.DWORD]
    handle=kernel.OpenProcess(0x410,False,pid)
    if not handle:return None
    counters=Counters();counters.cb=ctypes.sizeof(counters)
    try:
        if api.GetProcessMemoryInfo(handle,ctypes.byref(counters),counters.cb):return dict(working_mib=counters.working/2**20,private_mib=counters.private/2**20)
    finally:kernel.CloseHandle(handle)

with tempfile.TemporaryDirectory(prefix='pixel-bench-',dir=root/'.runtime') as folder:
    import beatlight.ui.pixel as pixel_ui
    asset=(root/'beatlight/beatlight_pixel_studio.html').read_text(encoding='utf-8')
    if args.reference_wheel:
        with ZipFile(args.reference_wheel) as archive:asset=archive.read(next(name for name in archive.namelist() if name.endswith('/beatlight_pixel_studio.html'))).decode('utf-8')
    asset=asset.replace("'use strict';","'use strict';let benchSeed=1337;Math.random=()=>((benchSeed=(Math.imul(benchSeed,1664525)+1013904223)>>>0)/4294967296);",1)
    asset_path=Path(folder)/'studio.html';asset_path.write_text(asset,encoding='utf-8');pixel_ui.studio_asset=lambda:asset_path
    window=MainWindow(SettingsStore(Path(folder)/'preferences.json'),Settings(source='synthetic'));window.show();window._navigate(9)
    def pump(condition,timeout=15):
        end=monotonic()+timeout
        while monotonic()<end:
            app.processEvents()
            if condition():return
            sleep(.002)
        assert condition(),window.pixel_page.notice.text()
    def js(expression):
        result=[];window.pixel_page.webpage.runJavaScript('JSON.stringify('+expression+')',result.append)
        pump(lambda:bool(result));return json.loads(result[0])
    report=dict(version=__version__,asset=args.reference_wheel.name if args.reference_wheel else 'current',seed=1337,single_auto=args.single,hardware_used=False,software_renderer=True,phases=[])
    try:
        pump(lambda:window.pixel_page.bridge.ready_state and not window.busy);window.timer.stop()
        js('(()=>{const p=BeatlightPixel.project();p.geometry.lines.forEach(l=>{l.leds=300;l.pixels=300});p.strips.forEach(s=>s.profile="ws2812");p.show.strobes=false;p.show.peakMode="off";p.show.sceneBars=16;BeatlightPixel.applyProject(p);BeatlightPixel.setInput("demo");BeatlightPixel.arm(true);return true})()')
        pid=window.pixel_page.webpage.renderProcessPid()
        phases=('auto','liquid','economy','inactive','minimized') if args.extended else ('auto','liquid')
        for mode in phases:
            if mode=='economy':
                if not js('typeof BeatlightPixel.setPreviewQuality==="function"'):
                    report['phases'].append(dict(mode=mode,supported=False));continue
                js('(BeatlightPixel.setPreviewQuality("economy"),true)')
            elif mode=='inactive':js('(BeatlightPixel.arm(false),true)')
            elif mode=='minimized':window.showMinimized();window._tick()
            else:js('(()=>{const p=BeatlightPixel.project();p.show.mode='+json.dumps(mode)+';BeatlightPixel.applyProject(p);return true})()')
            if mode=='auto' and args.single:js('(BeatlightPixel.setEffectMix("single"),true)')
            start=monotonic();pump(lambda:monotonic()-start>.8)
            before=js('BeatlightPixel.status()');started=monotonic();first_cpu=cpu(pid);first_parent=cpu(os.getpid())
            pump(lambda:monotonic()-started>=args.seconds,args.seconds+3)
            after=js('BeatlightPixel.status()');elapsed=monotonic()-started;last_cpu=cpu(pid)
            a=before['render_ms'];b=after['render_ms'];frames=b['frames']-a['frames']
            report['phases'].append(dict(mode=mode,seconds=elapsed,frames=frames,fps=frames/elapsed,
                pattern=after['pattern'],canvas=js('[document.getElementById("stage").width,document.getElementById("stage").height]'),
                draw_ms=(b['average']*b['frames']-a['average']*a['frames'])/max(1,frames),
                renderer_cpu_percent=(last_cpu-first_cpu)/elapsed*100 if first_cpu is not None and last_cpu is not None else None,
                parent_cpu_percent=(cpu(os.getpid())-first_parent)/elapsed*100 if first_parent is not None else None,
                renderer_memory=memory(pid),parent_memory=memory(os.getpid()),
                texture_bytes=after['performance']['texture_bytes'],
                ticks=b.get('ticks',0)-a.get('ticks',0),preview=after['rendering'],target_fps=after['performance'].get('previewFps'),
                readback_pixels=b.get('readbackPixels',0)-a.get('readbackPixels',0),
                allocations=after['performance']['allocations']-before['performance']['allocations'],
                errors=list(window.pixel_page.render_errors)))
    finally:
        window.timer.start();window.close();pump(lambda:window.closed_ready)
args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
