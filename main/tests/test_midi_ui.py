import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from copy import deepcopy
from threading import Event
from time import monotonic,sleep
from types import SimpleNamespace
import pytest
from PySide6.QtWidgets import QApplication
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.ui.window import MainWindow
from beatlight.midi.mapping import ACTIONS,read_profile,wire
from beatlight.midi.runtime import MidiRuntime
from midi_fake import FakeMidiBackend


def pump(app,condition,timeout=5):
    end=monotonic()+timeout
    while monotonic()<end:
        app.processEvents()
        if condition():return
        sleep(.003)
    assert condition()


@pytest.fixture
def window(tmp_path):
    app=QApplication.instance() or QApplication([])
    window=MainWindow(SettingsStore(tmp_path/'preferences.json'),Settings(source='synthetic'));window.show()
    pump(app,lambda:not window.busy and bool(window.devices));window.timer.stop()
    yield app,window
    window.timer.start();window.close();pump(app,lambda:window.closed_ready)


def test_learn_boundaries_discard_stale_gestures_without_executing_or_arming_usb(window):
    app,owner=window;page=owner.midi_page;backend=FakeMidiBackend();page.runtime=MidiRuntime(lambda:backend);page.runtime.connect(0)
    pump(app,lambda:page.runtime.status().state=='connected')
    device=backend.devices[-1];old=dict(kind='note',channel=1,number=36);new=dict(kind='note',channel=1,number=37)
    device.emit(wire(old,127));page.learn.setChecked(True)
    device.emit(wire(new,127));pump(app,lambda:page.mapper.candidate is not None)
    device.emit(wire(new,127));page.learn.setChecked(False);page._poll()
    assert page.mapper.profile['mappings']['drop']['input']['number']==37
    assert not owner.pixel_page._control_commands and not owner.pixel_page.usb.runtime.status().armed
    assert not page.path.exists()


def test_profile_save_runs_off_ui_and_preserves_edits_made_during_the_write(window,monkeypatch):
    app,owner=window;page=owner.midi_page;entered=Event();release=Event()
    import beatlight.ui.midi as module
    original=module.save_profile
    def delayed(path,data):entered.set();release.wait(3);original(path,data)
    monkeypatch.setattr(module,'save_profile',delayed)
    try:
        page._save();assert entered.wait(1) and page._saving and not page.save.isEnabled()
        profile=deepcopy(page.mapper.profile);profile['mappings']['groove']['input']=dict(kind='note',channel=1,number=38,mode='absolute')
        page.mapper.configure(profile);page._changed();assert not page.path.exists()
        release.set();pump(app,lambda:not page._saving)
        assert page.dirty and page.mapper.profile['mappings']['groove']['input']['number']==38
        assert read_profile(page.path)['mappings']['groove']['input'] is None
        page._save();pump(app,lambda:not page._saving)
        assert not page.dirty and read_profile(page.path)['mappings']['groove']['input']['number']==38
    finally:release.set();pump(app,lambda:not page._saving)


def test_peak_commands_coalesce_while_a_renderer_request_is_in_flight(window):
    _,owner=window;page=owner.pixel_page;calls=[];page.bridge.ready_state=True
    page.webpage=SimpleNamespace(runJavaScript=lambda *args:calls.append(args))
    assert page.queue_controls([('peak_level',0)]) and len(calls)==1
    for i in range(1000):assert page.queue_controls([('peak_level',i/1000)])
    assert len(page._control_commands)==1 and len(calls)==1
    page.queue_controls([('drop',None)]);calls[0][1](True)
    assert len(calls)==2 and '0.999' in calls[1][0] and 'drop' in calls[1][0]
    calls[1][1](True);assert not page._control_busy and not page._control_commands


def test_unresponsive_renderer_blocks_new_commands_until_reset_and_ignores_late_callbacks(window):
    app,owner=window;page=owner.pixel_page;calls=[];page.bridge.ready_state=True
    page.webpage=SimpleNamespace(runJavaScript=lambda *args:calls.append(args))
    page.queue_controls([('drop',None)]);page.queue_controls([('auto',None)])
    pump(app,lambda:page.control_blocked,timeout=2)
    assert not page._control_commands and len(calls)==1
    calls[0][1](True);assert not page.queue_controls([('groove',None)]) and len(calls)==1
    page._reset_commands();assert page.queue_controls([('auto',None)]) and len(calls)==2
    calls[1][1](True)


def test_legacy_panels_are_disabled_by_default_and_can_be_restored_without_replacing_audio(window):
    app,owner=window;capture=owner.runtime
    assert not owner.settings.legacy_panels_enabled and not owner.light_runtime.running
    assert not owner.nav_group.button(6).isVisible() and not owner.nav_group.button(7).isVisible()
    owner.legacy_panels.setChecked(True);assert owner.light_runtime.running
    assert owner.nav_group.button(6).isVisible() and owner.nav_group.button(7).isVisible()
    owner._navigate(6);assert owner.pages.currentIndex()==6
    owner._navigate(0);owner.legacy_panels.setChecked(False)
    assert not owner.nav_group.button(6).isVisible() and owner.runtime is capture
    assert not owner.store.load().legacy_panels_enabled


def test_editing_a_led_address_during_its_test_keeps_feedback_bounded(window):
    app,owner=window;page=owner.midi_page;backend=FakeMidiBackend();page.runtime=MidiRuntime(lambda:backend);page.runtime.connect(0,0)
    pump(app,lambda:page.runtime.status().state=='connected')
    profile=deepcopy(page.mapper.profile)
    for index,mapping in enumerate(profile['mappings'].values()):mapping['output']=dict(kind='note',channel=1,number=36+index,on=127,off=0)
    page.mapper.configure(profile);page._refresh_table();page.table.selectRow(0);page._test_led()
    profile['mappings']['drop']['output']['number']=96;page.mapper.configure(profile);page._poll()
    assert len(page.runtime._feedback)==len(ACTIONS) and ('note',1,96) in page.runtime._feedback and ('note',1,36) not in page.runtime._feedback
