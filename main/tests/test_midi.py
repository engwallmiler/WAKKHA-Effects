import ctypes
from copy import deepcopy
from time import monotonic,sleep
from types import SimpleNamespace
import pytest
from beatlight.midi.mapping import (MidiMapper,default_profile,decode,save_profile,read_profile,validate_profile,wire)
from beatlight.midi.runtime import MidiRuntime
from beatlight.midi.winmm import InCaps,OutCaps,WinmmPort


def binding(kind='note',channel=1,number=36,mode='absolute'):
    return dict(kind=kind,channel=channel,number=number,mode=mode)


def configured(action='drop',kind='note',mode='absolute'):
    profile=default_profile();profile['mappings'][action]['input']=binding(kind=kind,mode=mode)
    return MidiMapper(profile)


def message(value=127,kind='note',channel=1,number=36):return wire(binding(kind,channel,number),value)


@pytest.mark.parametrize('word,expected',[(0x7f2490,('note',1,36,127)),(0x00248f,('note',16,36,0)),(0x4024b5,('cc',6,36,64)),(0xf8,None),(0xfe,None),(0x802490,None),(-1,None),(True,None)])
def test_short_message_decode_filters_clock_and_invalid_data(word,expected):assert decode(word)==expected


def test_learn_captures_first_control_silently_until_stopped_and_saved(tmp_path):
    mapper=configured();mapper.start_learn('breakdown')
    assert mapper.accept(message()) is None
    mapper.accept(message(number=40));assert mapper.candidate['number']==36
    # A conflicting assignment cannot overwrite the good association.
    with pytest.raises(ValueError,match='já está'):mapper.stop_learn()
    assert mapper.profile['mappings']['breakdown']['input'] is None
    mapper.start_learn('breakdown');mapper.accept(message(number=40));assert mapper.stop_learn()
    path=tmp_path/'midi.json';assert not path.exists()
    save_profile(path,mapper.profile);assert read_profile(path)==mapper.profile
    assert mapper.accept(message(number=40))==('breakdown',None)


@pytest.mark.parametrize('kind',['note','cc'])
def test_buttons_trigger_once_per_press_and_ignore_release_and_repeats(kind):
    mapper=configured(kind=kind)
    assert mapper.accept(message(kind=kind))==('drop',None)
    for _ in range(20):assert mapper.accept(message(kind=kind)) is None
    assert mapper.accept(message(0,kind=kind)) is None
    assert mapper.accept(message(kind=kind))==('drop',None)


@pytest.mark.parametrize('mode,positive,negative',[('relative_twos',1,127),('relative_binary',65,63),('relative_sign',1,65)])
def test_relative_encoders_preserve_all_steps_and_clamp(mode,positive,negative):
    mapper=configured('peak_level','cc',mode);mapper.peak=.5
    for _ in range(12):mapper.accept(message(positive,'cc'))
    assert mapper.peak==pytest.approx(.5+12/127)
    for _ in range(12):mapper.accept(message(negative,'cc'))
    assert mapper.peak==pytest.approx(.5)
    for _ in range(200):mapper.accept(message(positive,'cc'))
    assert mapper.peak==1


def test_note_velocity_level_ignores_release_and_absolute_cc_reaches_both_ends():
    mapper=configured('peak_level');assert mapper.accept(message(100))==('peak_level',100/127)
    assert mapper.accept(message(0)) is None and mapper.peak==100/127
    mapper=configured('peak_level','cc');assert mapper.accept(message(0,'cc'))==('peak_level',0)
    assert mapper.accept(message(127,'cc'))==('peak_level',1)


@pytest.mark.parametrize('change',[{'kind':'sysex'},{'channel':0},{'channel':True},{'number':128},{'mode':'unbounded'}])
def test_bad_bindings_never_replace_valid_saved_profile(tmp_path,change):
    mapper=configured();path=tmp_path/'midi.json';save_profile(path,mapper.profile);bad=deepcopy(mapper.profile)
    bad['mappings']['drop']['input'].update(change)
    with pytest.raises(ValueError):save_profile(path,bad)
    assert read_profile(path)==mapper.profile


def test_feedback_tracks_actual_modes_and_optional_detected_structure():
    profile=default_profile()
    for index,action in enumerate(profile['mappings']):profile['mappings'][action]['output']=dict(kind='note',channel=1,number=index,on=127,off=0)
    mapper=MidiMapper(profile);state=dict(mode='auto',manual_structure='breakdown',structure='breakdown',drop=False,continuous=False,queued=True,sync=True,peak_level=.5)
    output=mapper.feedback(state)
    assert decode(output[('note',1,1)][0])[3]==127  # manual breakdown
    assert decode(output[('note',1,7)][0])[3]==127  # Auto Show remains the base
    assert decode(output[('note',1,4)][0])[3]==64
    state['manual_structure']=None;assert decode(mapper.feedback(state)[('note',1,1)][0])[3]==0
    mapper.profile['detected_feedback']=True;assert decode(mapper.feedback(state)[('note',1,1)][0])[3]==127


def test_feedback_addresses_cannot_fight_and_unknown_profile_fields_are_not_actions():
    profile=default_profile();output=dict(kind='note',channel=1,number=36,on=127,off=0)
    profile['mappings']['drop']['output']=output;profile['mappings']['auto']['output']=dict(output)
    with pytest.raises(ValueError,match='já está'):validate_profile(profile)
    profile=default_profile();profile['mappings']['eval']={'input':None,'output':None}
    with pytest.raises(ValueError):validate_profile(profile)


def test_v1_profile_migrates_without_reassigning_the_existing_controls():
    old=default_profile();old['version']=1;del old['mappings']['cue_sync']
    old['mappings']['drop']['input']=dict(kind='note',channel=2,number=60,mode='absolute')
    migrated=validate_profile(old)
    assert migrated['version']==2 and migrated['mappings']['cue_sync']==dict(input=None,output=None)
    assert migrated['mappings']['drop']==old['mappings']['drop'] and 'cue_sync' not in old['mappings']


def test_reference_learn_triggers_once_per_press_and_its_led_tracks_the_marker():
    mapper=configured('cue_sync');assert mapper.accept(message())==('cue_sync',None)
    assert mapper.accept(message()) is None;mapper.accept(message(0));assert mapper.accept(message())==('cue_sync',None)
    mapper.profile['mappings']['cue_sync']['output']=dict(kind='note',channel=1,number=45,on=127,off=0)
    assert decode(mapper.feedback({'cue_sync':True})[('note',1,45)][0])[3]==127
    assert decode(mapper.feedback({'cue_sync':False})[('note',1,45)][0])[3]==0
    profile=default_profile();profile['version']=True
    with pytest.raises(ValueError):validate_profile(profile)


class FakeMidi:
    def __init__(self):self.sent=[];self.closed=False;self.callback=None
    def open(self,input_id,output_id,received):self.callback=received;return self
    def send(self,word):self.sent.append(word)
    def close(self):self.closed=True


def wait(condition,timeout=2):
    end=monotonic()+timeout
    while monotonic()<end:
        if condition():return
        sleep(.002)
    assert condition()


def test_runtime_sends_only_changes_clears_removed_leds_and_closes_dark():
    device=FakeMidi();runtime=MidiRuntime(lambda:device);runtime.connect(0,0)
    try:
        wait(lambda:runtime.status().state=='connected')
        key=('note',1,36);feedback={key:(message(),message(0))};runtime.set_feedback(feedback);wait(lambda:len(device.sent)==1)
        for _ in range(1000):runtime.set_feedback(feedback)
        assert device.sent==[message()]
        runtime.set_feedback({});wait(lambda:device.sent[-1]==message(0))
        runtime.set_feedback(feedback);wait(lambda:device.sent[-1]==message())
    finally:runtime.stop();wait(lambda:runtime.closed)
    assert device.closed and device.sent[-1]==message(0)


def test_input_queue_stays_bounded_filters_realtime_and_keeps_relative_order():
    runtime=MidiRuntime()
    for _ in range(10000):runtime.receive(0xf8)
    assert runtime.drain()==([],0)
    for i in range(32):runtime.receive(message(1 if i%2 else 127,'cc'))
    events,dropped=runtime.drain();assert len(events)==32 and not dropped
    for i in range(10000):runtime.receive(message(number=i%128))
    events,dropped=runtime.drain();assert len(events)==512 and dropped==9488


def test_input_only_connection_never_sends_feedback_even_on_close():
    device=FakeMidi();runtime=MidiRuntime(lambda:device);runtime.connect(0,None)
    try:
        wait(lambda:runtime.status().state=='connected');runtime.set_feedback({('note',1,36):(message(),message(0))})
    finally:runtime.stop();wait(lambda:runtime.closed)
    assert not device.sent and device.closed


def test_stop_between_idle_check_and_event_clear_never_strands_worker():
    from threading import Event
    device=FakeMidi();runtime=MidiRuntime(lambda:device)
    class ClosingEvent:
        def __init__(self):self.event=Event();self.clears=0
        def clear(self):
            self.event.clear();self.clears+=1
            if self.clears==2:runtime.stop();self.event.clear()
        def set(self):self.event.set()
        def wait(self):self.event.wait()
    runtime._wake=ClosingEvent();runtime.connect(0)
    try:wait(lambda:runtime.closed)
    finally:runtime.stop()
    assert device.closed


def test_partial_feedback_failure_still_turns_off_the_led_already_sent():
    class FailingMidi(FakeMidi):
        def send(self,word):
            if word==message(number=37):raise OSError('LED indisponível')
            super().send(word)
    device=FailingMidi();runtime=MidiRuntime(lambda:device);runtime.connect(0,0)
    try:
        wait(lambda:runtime.status().state=='connected')
        runtime.set_feedback({('note',1,n):(message(number=n),message(0,number=n)) for n in (36,37)})
        wait(lambda:runtime.closed)
    finally:runtime.stop()
    assert device.closed and device.sent==[message(),message(0)] and runtime.status().state=='error'


@pytest.mark.parametrize('input_id,output_id',[(-1,None),(True,None),(0,-1),(2**40,None),(0,2**40)])
def test_invalid_port_ids_are_rejected_without_opening(input_id,output_id):
    with pytest.raises(ValueError):MidiRuntime().connect(input_id,output_id)


def test_winmm_callback_keeps_64_bit_handles_and_only_delivers_short_messages():
    calls=[];received=[];big=0x1234567812345678
    def open_handle(pointer,*args):ctypes.cast(pointer,ctypes.POINTER(ctypes.c_void_p))[0]=ctypes.c_void_p(big);return 0
    def handle_call(handle,*args):calls.append(handle.value);return 0
    dll=SimpleNamespace(midiInOpen=open_handle,midiOutOpen=open_handle,midiInStart=handle_call,midiInStop=handle_call,midiInReset=handle_call,midiInClose=handle_call,midiOutClose=handle_call,midiOutShortMsg=handle_call)
    backend=SimpleNamespace(dll=dll,check=lambda *args:None);port=WinmmPort(backend,0,0,received.append)
    port.callback(ctypes.c_void_p(big),0x3c3,0,message(),0);assert received==[message()]
    port.send(message());port.close();assert all(handle==big for handle in calls)
    port.callback(ctypes.c_void_p(big),0x3c3,0,message(),0);assert received==[message()]
    assert ctypes.sizeof(InCaps)==76 and ctypes.sizeof(OutCaps)==84


def test_winmm_close_failure_retains_callback_and_still_closes_output(monkeypatch):
    import beatlight.midi.winmm as module
    monkeypatch.setattr(module,'_FAILED_PORT',None);calls=[]
    port=object.__new__(WinmmPort);port.input=ctypes.c_void_p(100);port.output=ctypes.c_void_p(200);port.closing=False;port.callback=object()
    def check(result,*_):
        if result:raise OSError('driver ocupado')
    dll=SimpleNamespace(midiInStop=lambda _:0,midiInReset=lambda _:0,midiInClose=lambda _:5,midiOutClose=lambda h:calls.append(h.value) or 0)
    port.backend=SimpleNamespace(dll=dll,check=check)
    with pytest.raises(OSError):port.close()
    assert calls==[200] and port.input.value==100 and port.output.value is None and module._FAILED_PORT is port
