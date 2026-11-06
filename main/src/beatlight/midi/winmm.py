"""MIDI curto do Windows: callback só entrega palavras; drivers ficam fora da GUI."""
import ctypes as c
from dataclasses import dataclass
import sys

_FAILED_PORT=None  # One retained callback if a broken driver refuses to close.


@dataclass(frozen=True)
class PortInfo:
    id: int
    name: str


class InCaps(c.Structure):
    _fields_=[('mid',c.c_uint16),('pid',c.c_uint16),('version',c.c_uint32),('name',c.c_wchar*32),('support',c.c_uint32)]


class OutCaps(c.Structure):
    _fields_=[('mid',c.c_uint16),('pid',c.c_uint16),('version',c.c_uint32),('name',c.c_wchar*32),
              ('technology',c.c_uint16),('voices',c.c_uint16),('notes',c.c_uint16),('mask',c.c_uint16),('support',c.c_uint32)]


class WinmmBackend:
    def __init__(self):
        if sys.platform!='win32':raise OSError('O backend MIDI desta versão usa o Windows. Áudio e Auto Show continuam disponíveis.')
        self.dll=c.WinDLL('winmm',use_last_error=True)
        signatures={'midiInGetNumDevs':[], 'midiOutGetNumDevs':[],
            'midiInGetDevCapsW':[c.c_size_t,c.POINTER(InCaps),c.c_uint],
            'midiOutGetDevCapsW':[c.c_size_t,c.POINTER(OutCaps),c.c_uint],
            'midiInOpen':[c.POINTER(c.c_void_p),c.c_uint,c.c_size_t,c.c_size_t,c.c_uint32],
            'midiOutOpen':[c.POINTER(c.c_void_p),c.c_uint,c.c_size_t,c.c_size_t,c.c_uint32],
            'midiOutShortMsg':[c.c_void_p,c.c_uint32],
            'midiInGetErrorTextW':[c.c_uint,c.c_wchar_p,c.c_uint],
            'midiOutGetErrorTextW':[c.c_uint,c.c_wchar_p,c.c_uint]}
        for name in ('midiInStart','midiInStop','midiInReset','midiInClose','midiOutClose'):signatures[name]=[c.c_void_p]
        for name,args in signatures.items():
            function=getattr(self.dll,name);function.argtypes=args;function.restype=c.c_uint

    def check(self,result,output=False):
        if not result:return
        text=c.create_unicode_buffer(256)
        getattr(self.dll,'midiOutGetErrorTextW' if output else 'midiInGetErrorTextW')(result,text,len(text))
        raise OSError(f'MIDI: {text.value or "erro de driver"} (código {result}). Confira a porta e o uso pelo Traktor.')

    def scan(self):
        groups=[]
        for output,caps_type in ((False,InCaps),(True,OutCaps)):
            prefix='midiOut' if output else 'midiIn';ports=[]
            for index in range(getattr(self.dll,prefix+'GetNumDevs')()):
                caps=caps_type();self.check(getattr(self.dll,prefix+'GetDevCapsW')(index,c.byref(caps),c.sizeof(caps)),output)
                ports.append(PortInfo(index,caps.name))
            groups.append(tuple(ports))
        return tuple(groups)

    def open(self,input_id,output_id,received):
        if _FAILED_PORT is not None:raise OSError('O driver MIDI não liberou a sessão anterior. Reinicie o aplicativo antes de reconectar o MIDI.')
        return WinmmPort(self,input_id,output_id,received)


class WinmmPort:
    def __init__(self,backend,input_id,output_id,received):
        self.backend=backend;self.input=c.c_void_p();self.output=c.c_void_p();self.closing=False
        callback_type=c.WINFUNCTYPE(None,c.c_void_p,c.c_uint,c.c_size_t,c.c_size_t,c.c_size_t)
        def callback(handle,message,instance,param1,param2):
            if not self.closing and message in (0x3c3,0x3cc):received(int(param1)&0xffffffff)
            elif not self.closing and message==0x3c2:received(None)
        self.callback=callback_type(callback)
        try:
            if output_id is not None:backend.check(backend.dll.midiOutOpen(c.byref(self.output),output_id,0,0,0),True)
            backend.check(backend.dll.midiInOpen(c.byref(self.input),input_id,c.cast(self.callback,c.c_void_p).value,0,0x30000))
            backend.check(backend.dll.midiInStart(self.input))
        except Exception:
            try:self.close()
            except Exception:pass
            raise

    def send(self,word):
        if self.output.value:self.backend.check(self.backend.dll.midiOutShortMsg(self.output,word),True)

    def close(self):
        global _FAILED_PORT
        self.closing=True;errors=[]
        if self.input.value:
            try:
                self.backend.dll.midiInStop(self.input);self.backend.dll.midiInReset(self.input)
                self.backend.check(self.backend.dll.midiInClose(self.input));self.input=c.c_void_p()
            except OSError as exc:errors.append(str(exc))
        if self.output.value:
            try:self.backend.check(self.backend.dll.midiOutClose(self.output),True);self.output=c.c_void_p()
            except OSError as exc:errors.append(str(exc))
        if errors:
            _FAILED_PORT=self
            raise OSError(' / '.join(errors))
        # Keep callback alive until midiInClose has completed successfully.
