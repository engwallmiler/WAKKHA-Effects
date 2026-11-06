from dataclasses import replace
import json
from types import SimpleNamespace
import pytest
from beatlight.pixel.usb import OutputStatus
from beatlight.diagnostics.output_log import OutputJournal
from test_pixel_usb_ui import panel,sources
import beatlight.ui.pixel_usb as module


class Runtime:
    closed=False
    def __init__(self):
        self.state=OutputStatus(state='connected',protocol=2,pixels=(300,0,0,0));self.frames=[];self.blackouts=0
    def status(self):return self.state
    def arm(self,enabled):self.state=replace(self.state,armed=bool(enabled))
    def blackout(self):self.blackouts+=1
    def submit(self,data,at):self.frames.append((data,at));return True
    def disconnect(self):self.closed=True


@pytest.fixture
def armed(panel,monkeypatch,tmp_path):
    control,calls=panel;clock=[100.];monkeypatch.setattr(module,'monotonic',lambda:clock[0])
    journal=OutputJournal(tmp_path/'logs');control.page.owner.output_journal=journal
    control._sources(json.dumps(sources()));control.runtime=Runtime()
    control.active_sources,control.active_pixels=control._mapping();control._arm(True)
    calls.clear();control.last_sources=100.;control.last_status=-10;control._last_tick=100.;control._tick()
    yield control,calls,clock,journal
    journal.close();journal._thread.join(3)


def frame(gate='emitindo'):
    return json.dumps({'version':2,'outputs':[{'id':'a','profile':'ws2812','model':'RGB','pixels':300,'leds':300,'data':[12,24,36]*300},None,None,None], 'diagnostics':{'gate':gate,'bpm':128,'beat':46080}})


def callback(calls):return next(call[1] for call in reversed(calls) if 'outputFrames' in call[0])


def codes(journal):return [row['code'] for row in journal.snapshot()['events']]


def test_short_stall_discards_old_frame_and_recovers_without_disarming_or_queuing(armed):
    control,calls,clock,journal=armed;old=callback(calls);count=len(calls)
    clock[0]+=.28;control._tick()
    assert control.runtime.status().armed and control.runtime.blackouts==1
    assert len(calls)==count and control._recovering
    old(frame());assert not control.runtime.frames and control._inflight is None
    clock[0]+=.03;control._tick();callback(calls)(frame())
    assert control.runtime.status().armed and len(control.runtime.frames)==1 and not control.error
    assert 'output.frame_gap' in codes(journal) and 'output.recovered' in codes(journal)
    assert 'output.frame_timeout' not in codes(journal)


def test_persistent_stall_disarms_and_waits_for_pending_callback_before_manual_reactivation(armed):
    control,calls,clock,journal=armed;old=callback(calls)
    clock[0]+=.8;control._tick()
    assert not control.runtime.status().armed and '750 ms' in control.error
    control._arm(True);assert not control.runtime.status().armed
    old(frame());assert not control.runtime.frames and control._inflight is None
    control._arm(True);assert control.runtime.status().armed
    assert journal.snapshot()['last_incident']['code']=='output.frame_timeout'


def test_manual_blackout_cancels_recovery_and_late_callback_cannot_rearm(armed):
    control,calls,clock,journal=armed;old=callback(calls)
    clock[0]+=.3;control._tick();control.off.click();old(frame())
    clock[0]+=.1;control._tick()
    assert not control.runtime.status().armed and not control.runtime.frames
    assert 'output.manual_stop' in codes(journal) and 'output.recovered' not in codes(journal)


def test_repeated_expired_callbacks_cannot_extend_the_recovery_budget(armed):
    control,calls,clock,journal=armed
    for _ in range(3):
        old=callback(calls);clock[0]+=.26;old(frame());control._tick()
    assert not control.runtime.status().armed and 'output.frame_timeout' in codes(journal)
    assert not control.runtime.frames


def test_silence_is_valid_zero_output_and_does_not_disarm(armed):
    control,calls,clock,journal=armed
    for _ in range(6):
        callback(calls)(frame('silencio'));clock[0]+=.15;control._tick()
    assert control.runtime.status().armed and len(control.runtime.frames)==6
    assert codes(journal).count('output.gate')==1
    assert len(journal.snapshot()['health'])>0


def test_invalid_frame_disarms_immediately_and_preserves_its_reason(armed):
    control,calls,clock,journal=armed;callback(calls)('{"error":"Fita incompatível"}')
    assert not control.runtime.status().armed and not control.runtime.frames
    assert journal.snapshot()['last_incident']['code']=='output.invalid_frame'
    control._arm(True)
    assert journal.snapshot()['last_incident']['message']=='Fita incompatível'


def test_old_preview_callback_cannot_release_a_new_preview_request(armed):
    control,calls,clock,journal=armed;old=callback(calls)
    control._bridge_ready();control._arm(True);control._tick();current=control._inflight
    old(frame())
    assert control._inflight==current and current is not None and not control.runtime.frames
    callback(calls)(frame());assert len(control.runtime.frames)==1
