"""Native Manual controls and new effects, four fake USB outputs, synthetic audio."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu --disable-gpu-compositing --no-sandbox')
from collections import deque
import json,sys,tempfile,zlib
from pathlib import Path
from time import monotonic,sleep
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from beatlight import __version__
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.pixel.project import PixelProjectStore
from beatlight.pixel.usb import PixelUsbOutput
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE

root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'tests'))
from pixel_usb_fake import FakeEsp32Port,INFO_MULTI
app=QApplication([]);app.setStyle('Fusion');app.setStyleSheet(STYLE)
if os.name=='nt':
    for name in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
report={'version':__version__,'physical_device_used':False,'patterns':[]}
from beatlight.dsp.pipeline import AudioAnalyzer
audit_started=monotonic();phase='startup';slow_audio=deque(maxlen=64);timeline=[]
process_audio=AudioAnalyzer.process
def measured_process(analyzer,block):
    at=monotonic();result=process_audio(analyzer,block);elapsed=(monotonic()-at)*1000
    if elapsed>25:slow_audio.append({'seconds':round(at-audit_started,3),'phase':phase,'ms':round(elapsed,2),'sequence':block.sequence})
    return result
AudioAnalyzer.process=measured_process
with tempfile.TemporaryDirectory(prefix='manual-patterns-',dir=root/'.runtime') as folder:
    directory=Path(folder);project=json.loads((root/'examples/quatro-saidas-ws2812.json').read_text(encoding='utf-8'))
    project['show'].update(mode='auto',peakMode='off',effectMix='layers',morphBeats=1,autoContinuous=False)
    for line in project['geometry']['lines']:line.update(leds=120,pixels=120)
    for strip in project['strips']:strip.update(profile='ws2812',effect='fire',response='kick')
    PixelProjectStore(directory/'pixel-studio.json').save(project)
    window=MainWindow(SettingsStore(directory/'preferences.json'),Settings(source='synthetic'))
    panel=window.pixel_page.usb;device=FakeEsp32Port(info=INFO_MULTI)
    device.frames=deque(maxlen=128);device.commands=deque(maxlen=256)
    panel.runtime=PixelUsbOutput(lambda _:device);window.show();window._navigate(9)
    def pump(condition,timeout=15):
        end=monotonic()+timeout
        while monotonic()<end:
            app.processEvents()
            if condition():return
            sleep(.003)
        assert condition(),(panel.error,panel.runtime.status(),list(window.pixel_page.render_errors))
    def settle(seconds):
        end=monotonic()+seconds;pump(lambda:monotonic()>=end,seconds+2)
    def js(expression):
        result={};window.pixel_page.webpage.runJavaScript('JSON.stringify('+expression+')',lambda value:result.update(value=value))
        pump(lambda:'value' in result);return json.loads(result['value'])
    def frames(count=3):
        before=panel.runtime.status().frames;pump(lambda:panel.runtime.status().frames>=before+count)
        assert len(device.frames[-1])==1440 and device.frames[-1][:360]==device.frames[-1][-360:]
        return bytes(device.frames[-1])
    feed=QTimer();feed.setInterval(40);started=monotonic();context='groove'
    def publish():
        now=monotonic();window.pixel_page.bridge.send_music({'version':1,'at':now,'sent_at':now,'active':True,'audible':True,'kick':None,
            'clock':{'beat':32+(now-started)*128/60,'bpm':128,'source':'link'},
            'music':{'state':context,'energy':.7,'tension':.8,'brightness':.5,'bass':.6,'density':.6,'activity':.5,'drop_id':1,'drop_kicks':1}})
    feed.timeout.connect(publish)
    try:
        pump(lambda:window.pixel_page.bridge.ready_state and not window.busy and bool(window.devices))
        window.source_combo.setCurrentIndex(window.source_combo.findData('synthetic'));window._start()
        pump(lambda:not window.busy and window.runtime.status().state=='running');window.timer.stop()
        panel.mode.setCurrentIndex(1);pump(lambda:panel.source.count()==4)
        for i,(source,enabled) in enumerate(zip(panel.sources,panel.output_enabled)):
            source.setCurrentIndex(i if i<3 else 0);enabled.setChecked(True)
        panel.port.clear();panel.port.addItem('USB EMULADO','FAKE-COM');panel._connect();pump(lambda:panel.runtime.status().state=='connected')
        js('(BeatlightPixel.setInput("live"),BeatlightPixel.arm(true),true)');feed.start();publish();panel._arm(True)
        frames();saved_strips=js('BeatlightPixel.project().strips');report['audio_dropped_before_manual']=window.runtime.status().dropped_blocks
        js('(document.getElementById("quickManual").click(),true)');assert js('BeatlightPixel.status().manual.active')
        nav=js('(()=>{const r=document.getElementById("manualNav").getBoundingClientRect();return {top:r.top,bottom:r.bottom,height:r.height,viewport:innerHeight}})()')
        assert nav['top']>=0 and nav['height']>0 and nav['bottom']<=nav['viewport']+1,nav
        report['navigation_visible_with_usb_panel']=nav
        first=js('BeatlightPixel.status().manual.pattern')
        js('(document.getElementById("manualNext").click(),true)');assert js('BeatlightPixel.status().manual.pattern')!=first
        js('(document.getElementById("manualPrevious").click(),true)');assert js('BeatlightPixel.status().manual.pattern')==first
        for index,pattern in enumerate(('standing','portals','zipper','diamonds','ribbons','silk')):
            phase=pattern;timeline.append({'phase':phase,'seconds':round(monotonic()-audit_started,3),'dropped':window.runtime.status().dropped_blocks})
            js('(document.getElementById("manualPatternSelect").value='+json.dumps(pattern)+',document.getElementById("manualPatternSelect").dispatchEvent(new Event("change")),true)')
            settle(.55);data=frames();assert any(data)
            assert js('BeatlightPixel.status().effect')==pattern and js('BeatlightPixel.status().manual.active')
            before=zlib.crc32(data);settle(.3);after=zlib.crc32(frames())
            assert before!=after
            report['patterns'].append({'id':pattern,'moving':True,'rgb_copy_exact':True,'sample_ms':panel._frame_timing.get('javascript_ms'),'audio_dropped':window.runtime.status().dropped_blocks})
            context=('buildup','drop','breakdown','groove')[index%4];publish();frames()
            assert js('BeatlightPixel.status().manual.pattern')==pattern and js('BeatlightPixel.status().manual.active')
        assert js('BeatlightPixel.project().strips')==saved_strips
        snapshot=js('BeatlightPixel.project()')
        assert snapshot['show']['manualMode'] and snapshot['show']['manualPattern']=='silk'
        window.showMinimized();before=frames();settle(.2);after=frames();assert before!=after
        assert js('BeatlightPixel.status().manual.active');window.showNormal()
        context='groove';publish();js('(document.getElementById("quickAuto").click(),true)')
        assert not js('BeatlightPixel.status().manual.active') and js('BeatlightPixel.project().strips')==saved_strips
        assert panel.runtime.status().armed and not panel.error
        report.update(manual_next_previous=True,manual_ignores_detected_structure=True,strip_settings_preserved=True,
            four_outputs_continuous=True,minimized_output=True,project_export_validated=True,
            audio_blocks=window.runtime.status().blocks,audio_dropped=window.runtime.status().dropped_blocks,
            usb_frames=panel.runtime.status().frames,errors=list(window.pixel_page.render_errors))
        report.update(slow_audio=list(slow_audio),timeline=timeline)
        (root/'docs'/'diagnostico-manual-audio-v0.44.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        assert not report['audio_dropped'] and not report['errors'],report
        assert not any(e['code']=='output.frame_timeout' for e in window.output_journal.snapshot()['events'])
        # Native screenshots/synchronous test-only export are outside real-time capture.
        # The application persists through its existing asynchronous writer.
        window.runtime.stop()
        assert window.grab().save(str(root/f'preview-manual-live-v{__version__}.png'))
        PixelProjectStore(directory/'exported-manual.json').save(snapshot)
    finally:
        feed.stop();window.timer.start();window.close();pump(lambda:window.closed_ready,20)
    report['closed_cleanly']=True;report['passed']=True
(root/'docs'/f'resultado-manual-patterns-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
