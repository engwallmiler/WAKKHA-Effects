"""Portas MIDI emuladas: entrada explícita e registro de retorno, sem hardware."""
from collections import deque
from beatlight.midi.winmm import PortInfo


class FakeMidiDevice:
    def __init__(self,received):self.received=received;self.sent=deque(maxlen=512);self.closed=False
    def emit(self,word):
        if not self.closed:self.received(word)
    def send(self,word):self.sent.append(word)
    def close(self):self.closed=True


class FakeMidiBackend:
    def __init__(self):self.devices=[]
    def scan(self):
        port=PortInfo(0,'Traktor Kontrol X1 · EMULADO');return (port,),(port,)
    def open(self,input_id,output_id,received):
        assert input_id==0 and output_id in (None,0)
        device=FakeMidiDevice(received);self.devices.append(device);return device
