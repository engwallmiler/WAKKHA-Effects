"""Visible Qt/WebEngine: queued JS vs stale RGB, real synthetic capture, fake USB."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu --disable-gpu-compositing --no-sandbox')
from collections import deque
import json,sys,tempfile
from pathlib import Path
from time import monotonic,sleep
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from beatlight import __version__
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.pixel.project import PixelProjectStore
from beatlight.pixel.usb import PixelUsbOutput
from beatlight.ui.window import MainWindow

root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'tests'))
from pixel_usb_fake import FakeEsp32Port,INFO_MULTI
app=QApplication([]);report={'version':__version__,'physical_device_used':False,'renderer_queued_tests':[]}
with tempfile.TemporaryDirectory(prefix='fresh-frame-',dir=root/'.runtime') as folder:
    directory=Path(folder);project=json.loads((root/'examples/quatro-saidas-ws2812.json').read_text(encoding='utf-8'))
    project['show'].update(mode='auto',effectMix='layers',layerCount=3,peakMode='off')
    for line in project['geometry']['lines']:line.update(leds=120,pixels=120)
    for strip in project['strips']:strip['profile']='ws2812'
    PixelProjectStore(directory/'pixel-studio.json').save(project)
    window=MainWindow(SettingsStore(directory/'preferences.json'),Settings(source='synthetic'))
    panel=window.pixel_page.usb;device=FakeEsp32Port(info=INFO_MULTI)
    device.frames=deque(maxlen=128);device.commands=deque(maxlen=256)
    panel.runtime=PixelUsbOutput(lambda _:device);window.show();window._navigate(9)
    def pump(condition,timeout=12):
        end=monotonic()+timeout
        while monotonic()<end:
            app.processEvents()
            if condition():return
            sleep(.002)
        assert condition(),(panel.error,panel.runtime.status(),list(window.pixel_page.render_errors))
    def settle(seconds):
        end=monotonic()+seconds;pump(lambda:monotonic()>=end,seconds+2)
    def js(expression):
        result={};window.pixel_page.webpage.runJavaScript('JSON.stringify('+expression+')',lambda value:result.update(value=value))
        pump(lambda:'value' in result);return json.loads(result['value'])
    def events():return window.output_journal.snapshot()['events']
    def count(code):return sum(row['code']==code for row in events())
    def stall(ms):window.pixel_page.webpage.runJavaScript(f'(()=>{{const stop=performance.now()+{ms};while(performance.now()<stop){{}}}})()')
    started=monotonic();feed=QTimer();feed.setInterval(40)
    def publish():
        now=monotonic();window.pixel_page.bridge.send_music({'version':1,'at':now,'sent_at':now,'active':True,'audible':True,'kick':None,
            'clock':{'beat':1060+(now-started)*127/60,'bpm':127,'source':'audio'},
            'music':{'state':'buildup','energy':.7,'tension':.9,'brightness':.6,'bass':.7,'density':.7,'activity':.5,'drop_id':0,'drop_kicks':0}})
    feed.timeout.connect(publish)
    original_callback=panel._frame_received
    try:
        pump(lambda:window.pixel_page.bridge.ready_state and not window.busy and bool(window.devices))
        window.source_combo.setCurrentIndex(window.source_combo.findData('synthetic'));window._start()
        pump(lambda:not window.busy and window.runtime.status().state=='running');window.timer.stop()
        panel.mode.setCurrentIndex(1);pump(lambda:panel.source.count()==4)
        for i,(source,enabled) in enumerate(zip(panel.sources,panel.output_enabled)):
            source.setCurrentIndex(i if i<3 else 0);enabled.setChecked(True)
        panel.port.clear();panel.port.addItem('USB EMULADO','FAKE-COM');panel._connect();pump(lambda:panel.runtime.status().state=='connected')
        js('(BeatlightPixel.setInput("live"),BeatlightPixel.arm(true),true)');feed.start();publish()
        panel._arm(True);pump(lambda:panel.runtime.status().frames>=10)
        health=js('BeatlightPixel.outputHealth()');assert health['preview_visible'] and not health['preview_low_power']
        assert panel.active_pixels==(120,)*4 and panel.active_sources[0]==panel.active_sources[3]
        report.update(preview_visible=True,presentation_light=False,effect_mix='layers',bpm=127,pixels=list(panel.active_pixels),fourth_output_copies_first=True)
        for delay in (400,594,594):
            previous=count('output.recovered');stall(delay)
            pump(lambda:count('output.recovered')>previous)
            assert panel.runtime.status().armed and count('output.frame_timeout')==0
            recovered=next(row for row in reversed(events()) if row['code']=='output.recovered')
            timing=recovered['context']['frame_timing']
            assert timing['age_bound_ms']<250 and timing['roundtrip_ms']>250
            report['renderer_queued_tests'].append({'block_ms':delay,**timing})
            frames=panel.runtime.status().frames;pump(lambda:panel.runtime.status().frames>frames+3)
        delayed={'scheduled':False,'rejected':False}
        def delayed_delivery(payload,serial,generation,source,at):
            if delayed['scheduled']:return original_callback(payload,serial,generation,source,at)
            delayed['scheduled']=True
            def deliver():
                before=panel.runtime.status().frames;original_callback(payload,serial,generation,source,at)
                assert panel._frame_timing['age_bound_ms']>250 and panel.runtime.status().frames==before
                delayed['rejected']=True
            QTimer.singleShot(594,deliver)
        previous=count('output.recovered');panel._frame_received=delayed_delivery
        pump(lambda:delayed['rejected']);pump(lambda:count('output.recovered')>previous)
        panel._frame_received=original_callback
        assert panel.runtime.status().armed and count('output.frame_timeout')==0
        report['594ms_old_rgb_delivery_rejected']=True
        stall(1100);pump(lambda:not panel.runtime.status().armed);pump(lambda:panel._inflight is None)
        before=panel.runtime.status().frames;settle(.15);assert panel.runtime.status().frames==before
        report['persistent_stall_still_requires_manual_rearm']=True
        panel._arm(True);pump(lambda:panel.runtime.status().frames>before+3)
        stall(594);QTimer.singleShot(100,lambda:panel._off());pump(lambda:not panel.runtime.status().armed)
        pump(lambda:panel._inflight is None);before=panel.runtime.status().frames;settle(.15)
        assert panel.runtime.status().frames==before
        report['manual_off_cannot_be_overridden_by_fresh_callback']=True
        report['audio_blocks']=window.runtime.status().blocks;report['audio_dropped']=window.runtime.status().dropped_blocks
        assert report['audio_blocks']>0 and report['audio_dropped']==0
        report['usb_frames']=before;report['render_errors']=list(window.pixel_page.render_errors)
        assert not report['render_errors']
    finally:
        panel._frame_received=original_callback;feed.stop();window.timer.start();window.close();pump(lambda:window.closed_ready,20)
    report['closed_cleanly']=True;report['passed']=True
(root/'docs'/f'resultado-frame-freshness-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
