"""Qt + MIDI Learn/LEDs + quatro saídas USB, usando exclusivamente emuladores."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu --disable-gpu-compositing --no-sandbox')
from pathlib import Path
from collections import deque
from time import monotonic,sleep
import json,sys,tempfile
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication,QEvent
from PySide6.QtGui import QFontDatabase
from beatlight import __version__
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE
from beatlight.midi.runtime import MidiRuntime
from beatlight.midi.mapping import ACTIONS,read_profile,wire,decode
from beatlight.pixel.usb import PixelUsbOutput
from beatlight.pixel.usb_protocol import BLACKOUT
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'tests'))
from midi_fake import FakeMidiBackend
from pixel_usb_fake import FakeEsp32Port,INFO_MULTI
app=QApplication([]);app.setStyle('Fusion');app.setStyleSheet(STYLE)
if os.name=='nt':
    for name in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
report=dict(version=__version__,physical_midi_used=False,physical_esp32_used=False,latency_ms=[])
with tempfile.TemporaryDirectory(prefix='pixel-midi-',dir=root/'.runtime') as folder:
    window=MainWindow(SettingsStore(Path(folder)/'preferences.json'),Settings(source='synthetic'));panel=window.pixel_page.usb;midi=window.midi_page
    backend=FakeMidiBackend();midi.runtime=MidiRuntime(lambda:backend)
    usb=FakeEsp32Port(info=INFO_MULTI);usb.frames=deque(maxlen=128);usb.commands=deque(maxlen=256);panel.runtime=PixelUsbOutput(lambda _:usb)
    window.show();window._navigate(9)
    def pump(condition,timeout=15):
        end=monotonic()+timeout
        while monotonic()<end:
            app.processEvents()
            if condition():return
            sleep(.003)
        assert condition(),(window.pixel_page.notice.text(),midi.notice.text(),panel.error,midi.runtime.status())
    def js(expression):
        result=[];window.pixel_page.webpage.runJavaScript('JSON.stringify('+expression+')',result.append);pump(lambda:bool(result));assert result[0];return json.loads(result[0])
    def frames(count=3):
        before=panel.runtime.status().frames;pump(lambda:panel.runtime.status().frames>=before+count);return bytes(usb.frames[-1])
    def emit(action,value=127):
        binding=midi.mapper.profile['mappings'][action]['input'];backend.devices[-1].emit(wire(binding,value))
    def press(action,condition):
        started=monotonic();emit(action);pump(condition);emit(action,0)
        report['latency_ms'].append(round((monotonic()-started)*1000,2))
    def screenshot(name):
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);assert window.grab().save(str(root/name))
    def led(number):
        return next((decode(word)[3] for word in reversed(backend.devices[-1].sent) if decode(word)[:3]==('note',1,number)),None)
    try:
        pump(lambda:window.pixel_page.bridge.ready_state and not window.busy);window.timer.stop()
        assert not window.settings.legacy_panels_enabled and not window.light_runtime.running
        project=json.loads((root/'examples/quatro-saidas-ws2812.json').read_text(encoding='utf-8'));js('BeatlightPixel.applyProject('+json.dumps(project)+')')
        panel.mode.setCurrentIndex(1);pump(lambda:panel.source.count()==4 and panel.refresh.isEnabled())
        for i,strip in enumerate(project['strips']):panel.sources[i].setCurrentIndex(panel.sources[i].findData(strip['id']));panel.output_enabled[i].setChecked(True)
        panel.port.clear();panel.port.addItem('EMULADO · sem ESP32 físico','EMULATED');panel.connect_button.click();pump(lambda:panel.runtime.status().state=='connected')
        js('(()=>{window.qaBeat=32;window.qaState="groove";window.qaAudible=true;const base='+str(monotonic())+',origin=performance.now();window.qaFeed=()=>BeatlightPixel.receive({version:1,at:100,sent_at:base+(performance.now()-origin)/1000,active:true,audible:qaAudible,kick:null,clock:{beat:qaBeat,bpm:120,source:"link"},music:{state:qaState,energy:.7,tension:.2,brightness:.5,bass:.6,density:.6,activity:.4,drop_id:1,drop_kicks:1}});BeatlightPixel.setInput("live");BeatlightPixel.arm(true);qaFeed();window.qaTimer=setInterval(qaFeed,40);return true})()')
        window.pixel_page.queue_controls([('auto',None)]);pump(lambda:window.pixel_page.bridge.controls.get('mode')=='auto')
        pump(lambda:panel.enable.isEnabled());panel.enable.click();assert any(frames())
        midi._scan();pump(lambda:not midi.scanning);midi.output.setCurrentIndex(1);midi.connect_button.click();pump(lambda:midi.runtime.status().state=='connected' and midi.learn.isEnabled())
        before_peak=js('BeatlightPixel.project().show.peakLevel')
        for index,action in enumerate(ACTIONS):
            midi.table.selectRow(index);midi.learn.click();assert midi.mapper.learning==action
            raw={'kind':'cc' if action=='peak_level' else 'note','channel':1,'number':20 if action=='peak_level' else 36+index}
            backend.devices[-1].emit(wire(raw,100));pump(lambda:midi.mapper.candidate is not None);backend.devices[-1].emit(wire(raw,0))
            state=js('BeatlightPixel.status()')
            # AUTO may evolve while learning. Only MIDI interventions must stay
            # silent; never freeze the automatic show to make this test pass.
            assert not midi.save.isEnabled() and state['effect']=='auto' and not state['manualDrop']
            assert state['operator']==dict(manualStructure=None,nextCombinationBeat=None)
            assert state['reference']['origin'] is None
            assert js('BeatlightPixel.project().show.peakLevel')==before_peak
            midi.learn.click();assert midi.mapper.learning is None
            assert midi.mapper.profile['mappings'][action]['input']=={**raw,'mode':'absolute'},(action,midi.notice.text())
            midi.copy_feedback.click()
        assert not midi.path.exists();midi.save.click();pump(lambda:not midi._saving);assert read_profile(midi.path)==midi.mapper.profile
        report.update(learn_all_actions=len(ACTIONS),learn_never_executes=True,explicit_save_verified=True)
        js('(BeatlightPixel.setEffectMix("single"),true)');assert js('BeatlightPixel.status().patternSources.length')==1
        report['single_four_outputs']=True
        press('breakdown',lambda:window.pixel_page.bridge.controls.get('manual_structure')=='breakdown');pump(lambda:led(37)==127)
        js('(qaState="buildup",qaFeed(),true)');frames();assert window.pixel_page.bridge.controls['manual_structure']=='breakdown'
        js('(qaState="groove",qaFeed(),true)');press('breakdown',lambda:window.pixel_page.bridge.controls.get('manual_structure') is None);pump(lambda:led(37)==0)
        press('buildup',lambda:window.pixel_page.bridge.controls.get('manual_structure')=='buildup')
        press('groove',lambda:window.pixel_page.bridge.controls.get('manual_structure')=='groove')
        press('auto',lambda:window.pixel_page.bridge.controls.get('mode')=='auto' and window.pixel_page.bridge.controls.get('manual_structure') is None)
        pump(lambda:led(43)==127)
        press('organic',lambda:window.pixel_page.bridge.controls.get('mode')=='organic')
        press('continuous',lambda:window.pixel_page.bridge.controls.get('continuous') is True)
        press('continuous',lambda:window.pixel_page.bridge.controls.get('mode')=='auto' and not window.pixel_page.bridge.controls.get('continuous'))
        for value in (0,127):emit('peak_level',value);pump(lambda v=value:window.pixel_page.bridge.controls.get('peak_level')==v/127)
        press('sync_1_8',lambda:window.pixel_page.bridge.controls.get('sync') is True);assert js('BeatlightPixel.status().beat')<.4
        before=js('BeatlightPixel.status().composition_id');press('next_combo',lambda:window.pixel_page.bridge.controls.get('queued') is True)
        assert js('BeatlightPixel.status().composition_id')==before
        js('(qaBeat+=4,qaFeed(),true)');pump(lambda:window.pixel_page.bridge.controls.get('queued') is False);assert js('BeatlightPixel.status().composition_id')!=before
        press('breakdown',lambda:window.pixel_page.bridge.controls.get('manual_structure')=='breakdown')
        press('drop',lambda:window.pixel_page.bridge.controls.get('drop') is True);assert window.pixel_page.bridge.controls.get('manual_structure') is None
        pump(lambda:led(36)==127);js('(qaBeat+=7,qaFeed(),true)');frames();assert window.pixel_page.bridge.controls.get('drop') is True
        js('(qaBeat+=1,qaFeed(),true)');pump(lambda:window.pixel_page.bridge.controls.get('drop') is False);pump(lambda:led(36)==0)
        press('cue_sync',lambda:window.pixel_page.bridge.controls.get('cue_sync',False));pump(lambda:led(46)==127)
        reference=js('BeatlightPixel.status().reference');assert reference['origin'] is not None
        report.update(manual_hold_and_toggles=True,show_modes_clear_manual=True,immediate_eight_beat_drop=True,quantized_next_combination=True,peak_full_range=True,led_state_feedback=True,reference_midi_and_led=True)
        window.showMinimized();press('groove',lambda:window.pixel_page.bridge.controls.get('manual_structure')=='groove')
        old_origin=js('BeatlightPixel.status().reference.origin');js('(qaBeat+=4,qaFeed(),true)')
        press('cue_sync',lambda:js('BeatlightPixel.status().reference.origin')>old_origin+1)
        assert window.pixel_page.bridge.controls.get('manual_structure')=='groove'
        report['reference_midi_while_minimized']=True
        frames(6);window.showNormal()
        press('auto',lambda:window.pixel_page.bridge.controls.get('manual_structure') is None)
        window.legacy_panels.setChecked(True);assert window.light_runtime.running and window.nav_group.button(6).isVisible()
        window.legacy_panels.setChecked(False);assert not window.nav_group.button(6).isVisible()
        report.update(minimized_midi_and_usb=True,legacy_toggle_reversible=True)
        window._navigate(10);midi.table.selectRow(1);midi.learn.click();emit('breakdown');pump(lambda:midi.mapper.candidate is not None);emit('breakdown',0)
        screenshot(f'preview-midi-learn-v{__version__}.png');midi.learn.click();midi.save.click();pump(lambda:not midi._saving)
        window._navigate(9);panel.fold.setChecked(False);press('breakdown',lambda:window.pixel_page.bridge.controls.get('manual_structure')=='breakdown');js('(document.getElementById("manualFold").open=true,true)');frames()
        screenshot(f'preview-midi-estrutura-v{__version__}.png');press('auto',lambda:window.pixel_page.bridge.controls.get('manual_structure') is None)
        js('(qaAudible=false,qaFeed(),true)');pump(lambda:not any(usb.frames[-1]));report['quiet_audio_all_outputs_dark']=True
        assert not window.pixel_page.control_blocked;assert not window.pixel_page.render_errors
        report.update(rgb_frame_bytes=len(usb.frames[-1]),usb_frames=panel.runtime.status().frames,midi_received=midi.runtime.status().received,midi_sent=midi.runtime.status().sent,errors=[])
        js('(clearInterval(qaTimer),true)')
    finally:
        window.timer.start();window.close();pump(lambda:window.closed_ready)
    assert usb.closed and usb.commands[-1].kind==BLACKOUT
    assert backend.devices[-1].closed and all(decode(word)[3]==0 for word in list(backend.devices[-1].sent)[-len(ACTIONS):])
    report.update(closed_cleanly=True,passed=True)
(root/'docs'/f'resultado-pixel-midi-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
