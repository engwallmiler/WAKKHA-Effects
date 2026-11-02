from types import SimpleNamespace
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtCore import QObject,Signal
from PySide6.QtWidgets import QApplication,QWidget
from beatlight.ui.pixel_usb import PixelUsbPanel


@pytest.fixture
def panel(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    class Bridge(QObject):
        operatorChanged=Signal()
        previewRequested=Signal()
        connected=Signal()
        ready_state=False
        operator={}
    calls=[];page=QWidget();page.owner=SimpleNamespace(store=SimpleNamespace(path=tmp_path/'preferences.json'),visuals_active=True)
    page.bridge=Bridge();page.view=None;page.webpage=SimpleNamespace(runJavaScript=lambda *args:calls.append(args));page.reload_preview=lambda:None
    monkeypatch.setattr(PixelUsbPanel,'_scan',lambda self:None)
    control=PixelUsbPanel(page);control.timer.stop();page.bridge.ready_state=True;page.view=object();control.mode.setCurrentIndex(1)
    yield control,calls
    control.shutdown();page.close();page.deleteLater();app.processEvents()


def sources():
    return [{'id':'a','name':'Outra fita','leds':300,'pixels':300,'profile':'ws2812'},
            {'id':'b','name':'Minha fita','leds':120,'pixels':120,'profile':'ws2811'}]


def test_preparation_uses_selected_real_count_and_rejects_an_older_source_refresh(panel):
    control,calls=panel;old=sources();control._sources(json.dumps(old));control.source.setCurrentIndex(1)
    assert control.pixel_count.value()==120
    old_revision=control.source_revision;control._prepare();generation=control.generation
    assert 'prepareWs2812("b",120)' in calls[-1][0]
    assert not control.source.isEnabled() and not control.enable.isEnabled()
    updated=sources();updated[1]['profile']='ws2812'
    control._prepared(json.dumps({'sources':updated}),generation,'b')
    assert control.source.currentData()=='b' and control.pixel_count.value()==120
    assert 'Pronta: Minha fita' in control.source_info.text() and not control.runtime.status().armed
    control._sources(json.dumps(old),old_revision)
    assert control.source_metadata['b']['profile']=='ws2812'
    assert json.loads(control.path.read_text(encoding='utf-8'))['strip_id']=='b'


def test_source_refresh_preserves_user_selection_and_failed_preparation_explains_the_reason(panel):
    control,_=panel;data=sources();control._sources(json.dumps(data));control.source.setCurrentIndex(1)
    data[0]['name']='Outra fita renomeada';control._sources(json.dumps(data))
    assert control.source.currentData()=='b' and control.pixel_count.value()==120
    control._prepare();control._prepared(json.dumps({'error':'Cópia exata exige a mesma quantidade de pixels.'}),control.generation,'b')
    assert 'Cópia exata' in control.error and not control.preparing
    assert control.source.currentData()=='b' and not control.runtime.status().armed


def test_cancelled_or_timed_out_preparation_cannot_restore_stale_sources(panel):
    control,_=panel;control._sources(json.dumps(sources()));control.source.setCurrentIndex(1)
    control._prepare();generation=control.generation;control.preparing_at-=3;control._tick()
    assert not control.preparing and 'não respondeu' in control.error
    control._prepared(json.dumps({'sources':sources()[:1]}),generation,'b')
    assert control.source.currentData()=='b' and 'não respondeu' in control.error


def test_blackout_invalidates_a_nonzero_sample_already_in_flight():
    calls=[]
    runtime=SimpleNamespace(blackout=lambda:calls.append('blackout'),submit=lambda *args:calls.append('frame'))
    panel=SimpleNamespace(page=SimpleNamespace(bridge=SimpleNamespace(operator={'blackout':True,'armed':True})),
        runtime=runtime,generation=7,pending=True,closing=False)
    PixelUsbPanel._operator_changed(panel)
    # A completed pre-blackout sample must not relight the strip after the command.
    PixelUsbPanel._frame(panel,'stale nonzero frame',7,'strip-1',0)
    assert calls==['blackout'] and not panel.pending


def test_other_operator_updates_do_not_cancel_a_valid_sample_or_flash_black():
    calls=[]
    panel=SimpleNamespace(page=SimpleNamespace(bridge=SimpleNamespace(operator={'blackout':False,'armed':True,'manualDrop':True,'previewOnly':True})),
        runtime=SimpleNamespace(blackout=lambda:calls.append('blackout')),generation=7,pending=True)
    PixelUsbPanel._operator_changed(panel)
    assert calls==[] and panel.generation==7 and panel.pending
