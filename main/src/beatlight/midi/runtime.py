"""Uma thread de MIDI, entrada limitada e somente o último retorno de LEDs."""
from collections import deque
from dataclasses import dataclass,replace
from threading import Event,Lock,Thread
from beatlight.midi.winmm import WinmmBackend
from beatlight.midi.mapping import ACTIONS,decode


@dataclass(frozen=True)
class MidiStatus:
    state: str='disconnected'
    received: int=0
    sent: int=0
    dropped: int=0
    error: str=''


class MidiRuntime:
    def __init__(self,backend_factory=WinmmBackend):
        self.backend_factory=backend_factory;self._lock=Lock();self._wake=Event();self._stop=Event();self._thread=None
        self._status=MidiStatus();self._input=deque();self._feedback={}

    @property
    def closed(self):return self._thread is None or not self._thread.is_alive()

    def status(self):
        with self._lock:return self._status

    def receive(self,word):
        if word is None:
            with self._lock:self._status=replace(self._status,error='A entrada MIDI foi encerrada pelo dispositivo.')
            self._stop.set();self._wake.set();return
        # Filter realtime clock, sensing, SysEx and irrelevant channel messages
        # before touching the queue. Relative encoder increments must retain order.
        if type(word) is not int or not 0<=word<=0xffffffff or (word&0xf0) not in (0x80,0x90,0xb0):return
        with self._lock:
            self._status=replace(self._status,received=self._status.received+1)
            if len(self._input)<512:self._input.append(word)
            else:self._status=replace(self._status,dropped=self._status.dropped+1)

    def drain(self):
        with self._lock:
            events=list(self._input);self._input.clear();return events,self._status.dropped

    def set_feedback(self,feedback):
        if len(feedback)>len(ACTIONS):raise ValueError('Retorno MIDI excede as funções conhecidas.')
        for key,values in feedback.items():
            if not isinstance(values,tuple) or len(values)!=2 or any(decode(word) is None or decode(word)[:3]!=key for word in values):raise ValueError('Retorno LED MIDI inválido.')
        with self._lock:
            if feedback==self._feedback:return
            self._feedback=dict(feedback)
        self._wake.set()

    def connect(self,input_id,output_id=None):
        if not self.closed:raise ValueError('Desconecte a sessão MIDI anterior primeiro.')
        if type(input_id) is not int or not 0<=input_id<=65535 or output_id is not None and (type(output_id) is not int or not 0<=output_id<=65535):raise ValueError('Selecione uma entrada MIDI válida.')
        with self._lock:self._input.clear();self._feedback={};self._status=MidiStatus(state='connecting')
        self._stop.clear();self._wake.clear();self._thread=Thread(target=self._run,args=(input_id,output_id),name='pixel-midi',daemon=True);self._thread.start()

    def stop(self):self._stop.set();self._wake.set()

    def _run(self,input_id,output_id):
        port=None;previous={};error=''
        try:
            port=self.backend_factory().open(input_id,output_id,self.receive)
            with self._lock:self._status=replace(self._status,state='connected')
            while not self._stop.is_set():
                self._wake.clear()
                if self._stop.is_set():break
                with self._lock:desired=dict(self._feedback)
                if output_id is not None:
                    for key,values in tuple(previous.items()):
                        if key not in desired:port.send(values[1]);del previous[key]
                    for key,values in desired.items():
                        if previous.get(key)!=values:
                            port.send(values[0])
                            previous[key]=values
                            with self._lock:self._status=replace(self._status,sent=self._status.sent+1)
                previous=desired;self._wake.wait()
        except Exception as exc:error=str(exc) or type(exc).__name__
        finally:
            if port:
                if output_id is not None:
                    for values in previous.values():
                        try:port.send(values[1])
                        except Exception:pass
                try:port.close()
                except Exception as exc:error=error or str(exc)
            with self._lock:
                self._input.clear();self._feedback={}
                self._status=replace(self._status,state='error' if error or self._status.error else 'disconnected',error=error or self._status.error)
