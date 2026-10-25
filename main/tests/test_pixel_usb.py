import json
import struct
from time import monotonic,sleep
import pytest
from beatlight.pixel.usb_protocol import (ACK,HELLO,CONFIG,FRAME,BLACKOUT,HEADER,MAGIC,
    Decoder,Packet,OutputConfig,encode,device_info,rgb_payload)
from beatlight.pixel.usb import PixelUsbOutput
from pixel_usb_fake import FakeEsp32Port,INFO_DATA


def wait(condition,timeout=2):
    end=monotonic()+timeout
    while monotonic()<end:
        if condition():return
        sleep(.003)
    assert condition(),'Transporte USB não completou a operação'


def test_binary_protocol_recovers_noise_fragmentation_and_corruption():
    rgb=bytes(range(256))*3+bytes(132)
    frame=encode(FRAME,0xffffffff,rgb)
    corrupt=bytearray(frame);corrupt[120]^=1
    messages=[];decoder=Decoder()
    stream=b'ROM boot log\r\n'+bytes(corrupt)+frame+encode(BLACKOUT,0)
    for first in range(0,len(stream),7):messages.extend(decoder.feed(stream[first:first+7]))
    assert messages==[Packet(FRAME,0xffffffff,rgb),Packet(BLACKOUT,0,b'')]
    assert decoder.errors>=1 and len(decoder.buffer)<4


def test_invalid_length_header_does_not_block_the_next_valid_command():
    decoder=Decoder()
    invalid=HEADER.pack(MAGIC,FRAME,0,0xffff,12)
    assert decoder.feed(invalid+encode(HELLO,13))==[Packet(HELLO,13,b'')]
    assert decoder.errors==1


@pytest.mark.parametrize('values',[{'brightness':True},{'brightness':256},{'brightness':-1},
    {'milliamps':False},{'milliamps':499},{'milliamps':20001}])
def test_invalid_physical_limits_rejected(values):
    with pytest.raises(ValueError):OutputConfig(**values)


def test_configuration_has_exact_fixed_strip_size_and_conservative_defaults():
    assert struct.unpack('<HBH',OutputConfig().payload())==(300,64,2000)


@pytest.mark.parametrize('change',[{'device':'printer'},{'protocol':True},{'pixels':200},{'pin':2},{'order':'RGB'},{'watchdog_ms':0}])
def test_other_device_or_incompatible_firmware_rejected(change):
    with pytest.raises(ValueError):device_info(json.dumps({**INFO_DATA,**change}).encode())


def test_physical_frame_never_resamples_groups_or_accepts_rgbw():
    frame={'id':'a','profile':'ws2812','model':'RGB','pixels':300,'leds':300,'data':[12,0,255]*300}
    assert rgb_payload(frame,'a')==bytes([12,0,255])*300
    for change in ({'profile':'ws2811'},{'model':'RGBW'},{'pixels':200},{'leds':900},{'data':[0]*899},{'data':[False]*900},{'data':[256]*900}):
        with pytest.raises(ValueError):rgb_payload({**frame,**change},'a')


@pytest.fixture
def output():
    ports=[];runtimes=[]
    def create(**options):
        port=FakeEsp32Port(**options);runtime=PixelUsbOutput(lambda name:port)
        ports.append(port);runtimes.append(runtime);runtime.connect('FAKE-COM',OutputConfig())
        return runtime,port
    yield create
    for runtime in runtimes:runtime.disconnect()
    for runtime in runtimes:wait(lambda r=runtime:r.closed)


def test_connection_starts_dark_and_only_streams_after_explicit_arm(output):
    runtime,port=output();wait(lambda:runtime.status().state=='connected')
    assert not runtime.status().armed and not port.frames
    assert [c.kind for c in port.commands]==[HELLO,CONFIG]
    assert port.commands[1].payload==OutputConfig().payload()
    assert not runtime.submit(bytes(900))
    runtime.arm(True);assert runtime.submit(bytes([1,2,3])*300)
    wait(lambda:runtime.status().frames==1)
    assert port.frames==[bytes([1,2,3])*300]
    runtime.arm(False);wait(lambda:port.commands[-1].kind==BLACKOUT)
    assert not runtime.submit(bytes([255])*900)
    runtime.disconnect();wait(lambda:runtime.closed)
    assert port.closed and port.commands[-1].kind==BLACKOUT


def test_busy_device_receives_latest_frame_without_a_backlog(output):
    runtime,port=output(hold_frames=True);wait(lambda:runtime.status().state=='connected')
    runtime.arm(True);runtime.submit(bytes([1])*900);wait(lambda:len(port.frames)==1)
    for level in range(2,80):runtime.submit(bytes([level])*900)
    port.allow_ack.set();wait(lambda:runtime.status().frames==2)
    assert port.frames==[bytes([1])*900,bytes([79])*900]
    assert runtime.status().dropped>=77


def test_emergency_blackout_preempts_a_missing_frame_ack(output):
    runtime,port=output(hold_frames=True);wait(lambda:runtime.status().state=='connected')
    runtime.arm(True);runtime.submit(bytes([255])*900);wait(lambda:len(port.frames)==1)
    began=monotonic();runtime.arm(False)
    wait(lambda:port.commands[-1].kind==BLACKOUT,timeout=.15)
    assert monotonic()-began<.15 and runtime.status().state=='connected'


def test_missing_ack_fails_closed_and_requires_manual_reconnection(output):
    runtime,port=output(hold_frames=True);wait(lambda:runtime.status().state=='connected')
    runtime.arm(True);runtime.submit(bytes([255])*900)
    wait(lambda:runtime.closed)
    assert runtime.status().state=='error' and not runtime.status().armed
    assert port.closed and port.commands[-1].kind==BLACKOUT


def test_stale_producer_is_blacked_out_and_late_callbacks_are_rejected(output):
    runtime,port=output();wait(lambda:runtime.status().state=='connected')
    runtime.arm(True);runtime.submit(bytes([1])*900);wait(lambda:runtime.status().frames==1)
    wait(lambda:port.commands[-1].kind==BLACKOUT)
    assert runtime.status().armed and runtime.status().state=='connected'
    assert not runtime.submit(bytes([255])*900,monotonic()-.3)
    assert len(port.frames)==1
    runtime.submit(bytes([2])*900);wait(lambda:runtime.status().frames==2)


def test_handshake_can_be_cancelled_without_waiting_for_boot_timeout(output):
    runtime,port=output(answer_hello=False);wait(lambda:bool(port.commands))
    began=monotonic();runtime.disconnect();wait(lambda:runtime.closed,timeout=.15)
    assert monotonic()-began<.15 and port.closed
    assert all(c.kind==HELLO for c in port.commands)


def test_incompatible_device_never_receives_pixel_frames(output):
    runtime,port=output(info={**INFO_DATA,'pixels':150});wait(lambda:runtime.closed)
    assert runtime.status().state=='error' and not port.frames
    assert [c.kind for c in port.commands]==[HELLO]
