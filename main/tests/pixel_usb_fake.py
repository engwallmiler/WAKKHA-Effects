"""Emulador serial para exercitar o transporte; não representa temporização elétrica."""
import json
import struct
from threading import Lock,Event
from time import sleep
from beatlight.pixel.usb_protocol import ACK,INFO,HELLO,FRAME,CONFIG,Decoder,encode

INFO_DATA={'device':'BEATLIGHT-ESP32','protocol':1,'firmware':'0.22.0','pixels':300,
           'pin':18,'order':'GRB','watchdog_ms':750}


class FakeEsp32Port:
    def __init__(self,info=None,hold_frames=False,answer_hello=True):
        self.info=INFO_DATA if info is None else info
        self.answer_hello=answer_hello
        self.lock=Lock();self.buffer=bytearray();self.decoder=Decoder()
        self.commands=[];self.frames=[];self.closed=False;self.waiting=[]
        self.allow_ack=Event()
        if not hold_frames:self.allow_ack.set()

    @property
    def in_waiting(self):
        with self.lock:return len(self.buffer)

    def write(self,data):
        with self.lock:
            for packet in self.decoder.feed(data):
                self.commands.append(packet)
                if packet.kind==HELLO:
                    if self.answer_hello:self.buffer.extend(encode(INFO,packet.sequence,json.dumps(self.info).encode()))
                else:
                    ack=encode(ACK,packet.sequence,struct.pack('<BBI',packet.kind,0,123))
                    if packet.kind==FRAME:
                        self.frames.append(packet.payload)
                        if not self.allow_ack.is_set():self.waiting.append(ack);continue
                    self.buffer.extend(ack)
        return len(data)

    def read(self,count):
        with self.lock:
            if self.allow_ack.is_set() and self.waiting:
                for message in self.waiting:self.buffer.extend(message)
                self.waiting.clear()
            if self.buffer:
                data=bytes(self.buffer[:count]);del self.buffer[:count];return data
        sleep(.002);return b''

    def close(self):self.closed=True
