"""Saída USB em thread própria: quadro mais recente, ACK, blackout e prazos finitos."""
from dataclasses import dataclass,replace
from collections import deque
import struct
from threading import Event,Lock,Thread
from time import monotonic
from beatlight.pixel.usb_protocol import (ACK,INFO,HELLO,CONFIG,FRAME,BLACKOUT,BAUD,
    MAX_PAYLOAD,Decoder,OutputConfig,encode,device_info)


@dataclass(frozen=True)
class OutputStatus:
    state: str="disconnected"
    port: str=""
    armed: bool=False
    firmware: str=""
    frames: int=0
    dropped: int=0
    fps: float=0
    last_frame: float=0
    error: str=""


def list_ports():
    from serial.tools.list_ports import comports
    return [(p.device,f"{p.device} · {p.description}") for p in comports()]


def open_port(name):
    import serial
    port=serial.Serial(port=None,baudrate=BAUD,timeout=.01,write_timeout=.1)
    port.dtr=False;port.rts=False;port.port=name
    port.open()
    return port


class Cancelled(Exception):pass
class Superseded(Exception):pass


class PixelUsbOutput:
    def __init__(self,port_factory=open_port):
        self._factory=port_factory
        self._lock=Lock();self._stop=Event();self._wake=Event()
        self._thread=None;self._status=OutputStatus()
        self._pending=None;self._urgent=False
        self._sequence=0;self._decoder=Decoder()

    @property
    def closed(self):return self._thread is None or not self._thread.is_alive()

    def status(self):
        with self._lock:return self._status

    def _update(self,**values):
        with self._lock:self._status=replace(self._status,**values)

    def connect(self,port,config=OutputConfig()):
        if not self.closed:raise ValueError("Aguarde a conexão anterior encerrar.")
        if not isinstance(port,str) or not port or len(port)>128:raise ValueError("Selecione a porta COM do ESP32.")
        if not isinstance(config,OutputConfig):raise ValueError("Configuração USB inválida.")
        self._stop.clear();self._wake.clear();self._decoder=Decoder()
        with self._lock:
            self._status=OutputStatus(state="connecting",port=port)
            self._pending=None;self._urgent=False
        self._thread=Thread(target=self._run,args=(port,config),name="pixel-usb",daemon=True)
        self._thread.start()

    def arm(self,enabled):
        with self._lock:
            if enabled and self._status.state!="connected":raise ValueError("Conecte o ESP32 antes de ativar a saída.")
            self._status=replace(self._status,armed=bool(enabled))
            self._pending=None;self._urgent=not enabled
        self._wake.set()

    def blackout(self):
        with self._lock:self._pending=None;self._urgent=True
        self._wake.set()

    def submit(self,data,created_at=None):
        if not isinstance(data,bytes) or len(data)!=MAX_PAYLOAD:raise ValueError("São necessários 900 bytes RGB.")
        at=monotonic() if created_at is None else created_at
        now=monotonic()
        with self._lock:
            if self._status.state!="connected" or not self._status.armed:return False
            if not 0<=now-at<=.25:
                self._pending=None;self._urgent=True
                self._status=replace(self._status,dropped=self._status.dropped+1);return False
            if self._pending is not None:self._status=replace(self._status,dropped=self._status.dropped+1)
            self._pending=(data,at)
        self._wake.set();return True

    def disconnect(self):
        with self._lock:
            self._status=replace(self._status,armed=False,state="stopping" if not self.closed else "disconnected")
            self._pending=None;self._urgent=True
        self._stop.set();self._wake.set()

    def _send(self,port,kind,payload=b""):
        self._sequence=(self._sequence+1)&0xffffffff
        data=encode(kind,self._sequence,payload)
        if port.write(data)!=len(data):raise OSError("Escrita USB incompleta.")
        return self._sequence

    def _reply(self,port,kind,seq,timeout=.2,ignore_stop=False):
        end=monotonic()+timeout
        while monotonic()<end:
            if self._stop.is_set() and not ignore_stop:raise Cancelled()
            if kind==FRAME:
                with self._lock:urgent=self._urgent or not self._status.armed
                if urgent:raise Superseded()
            chunk=port.read(min(4096,max(1,port.in_waiting)))
            for reply in self._decoder.feed(chunk):
                if reply.sequence!=seq:continue
                if kind==HELLO and reply.kind==INFO:return device_info(reply.payload)
                if reply.kind==ACK and len(reply.payload)==6 and reply.payload[0]==kind:
                    command,result,_=struct.unpack("<BBI",reply.payload)
                    if result:raise OSError(f"ESP32 rejeitou comando {command} (código {result}).")
                    return True
        raise TimeoutError("ESP32 não confirmou o comando USB no prazo.")

    def _command(self,port,kind,payload=b"",ignore_stop=False):
        return self._reply(port,kind,self._send(port,kind,payload),ignore_stop=ignore_stop)

    def _run(self,name,config):
        port=None;verified=False;error="";count=0;ack_times=deque(maxlen=31)
        try:
            port=self._factory(name)
            deadline=monotonic()+3
            while True:
                if self._stop.is_set():raise Cancelled()
                try:info=self._command(port,HELLO);break
                except TimeoutError:
                    if monotonic()>=deadline:raise TimeoutError("Sem identificação BEATLIGHT-ESP32. Confira firmware, cabo USB e porta COM; feche o Monitor Serial.") from None
            verified=True
            self._command(port,CONFIG,config.payload())
            self._update(state="connected",firmware=info["firmware"])
            last_data=monotonic();last_send=0;blank=True
            while not self._stop.is_set():
                self._wake.clear();now=monotonic()
                with self._lock:
                    urgent=self._urgent;self._urgent=False
                    armed=self._status.armed
                    pending=self._pending if not urgent and now-last_send>=1/30 else None
                    if pending is not None:self._pending=None
                if urgent or (not blank and (not armed or now-last_data>.25)):
                    self._command(port,BLACKOUT);blank=True
                if armed and pending is not None and not urgent:
                    data,at=pending
                    if not 0<=monotonic()-at<=.25:
                        self._command(port,BLACKOUT);blank=True
                        with self._lock:self._status=replace(self._status,dropped=self._status.dropped+1)
                    else:
                        sent_at=monotonic()
                        try:self._command(port,FRAME,data)
                        except Superseded:continue
                        ack_at=monotonic();ack_times.append(ack_at)
                        while ack_times and ack_at-ack_times[0]>1:ack_times.popleft()
                        fps=(len(ack_times)-1)/max(.001,ack_times[-1]-ack_times[0])
                        last_send=sent_at;last_data=at;blank=False;count+=1
                        self._update(frames=count,last_frame=ack_at,fps=fps)
                self._wake.wait(.003)
        except Cancelled:pass
        except Exception as exc:error=str(exc) or type(exc).__name__
        finally:
            if port is not None:
                if verified:
                    try:self._command(port,BLACKOUT,ignore_stop=True)
                    except Exception:pass
                try:port.close()
                except Exception:pass
            with self._lock:
                self._pending=None;self._urgent=False
                self._status=replace(self._status,state="error" if error else "disconnected",armed=False,error=error)
