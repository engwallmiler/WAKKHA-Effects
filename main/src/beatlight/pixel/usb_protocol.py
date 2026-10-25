"""BLP1: quadros RGB binários, delimitados, com CRC32 e confirmação do ESP32."""
from dataclasses import dataclass
import json
import struct
import zlib

MAGIC=b"BLP1"
HEADER=struct.Struct("<4sBBHI")
CRC=struct.Struct("<I")
HELLO,CONFIG,FRAME,BLACKOUT=1,2,3,4
INFO,ACK=0x81,0x82
PIXELS=300
BAUD=921600
MAX_PAYLOAD=PIXELS*3


@dataclass(frozen=True)
class Packet:
    kind: int
    sequence: int
    payload: bytes


def encode(kind,sequence,payload=b""):
    if type(kind) is not int or not 0<=kind<=255 or type(sequence) is not int or not 0<=sequence<=0xffffffff:
        raise ValueError("Tipo/sequência BLP1 inválido.")
    if not isinstance(payload,bytes) or len(payload)>MAX_PAYLOAD:
        raise ValueError("Payload BLP1 inválido.")
    header=HEADER.pack(MAGIC,kind,0,len(payload),sequence)
    return header+payload+CRC.pack(zlib.crc32(header[4:]+payload))


class Decoder:
    def __init__(self):
        self.buffer=bytearray()
        self.errors=0

    def feed(self,data):
        self.buffer.extend(data)
        packets=[]
        while len(self.buffer)>=4:
            first=self.buffer.find(MAGIC)
            if first<0:
                del self.buffer[:-3]
                break
            if first:del self.buffer[:first]
            if len(self.buffer)<HEADER.size:break
            _,kind,reserved,length,seq=HEADER.unpack_from(self.buffer)
            if reserved or length>MAX_PAYLOAD:
                self.errors+=1;del self.buffer[0];continue
            total=HEADER.size+length+CRC.size
            if len(self.buffer)<total:break
            expected=CRC.unpack_from(self.buffer,total-CRC.size)[0]
            if zlib.crc32(self.buffer[4:total-CRC.size])!=expected:
                self.errors+=1;del self.buffer[0];continue
            packets.append(Packet(kind,seq,bytes(self.buffer[HEADER.size:total-CRC.size])))
            del self.buffer[:total]
        return packets


def device_info(payload):
    try:data=json.loads(payload)
    except (ValueError,UnicodeError):raise ValueError("Identificação ESP32 inválida.") from None
    if not isinstance(data,dict) or data.get("device")!="BEATLIGHT-ESP32" or type(data.get("protocol")) is not int or data["protocol"]!=1:
        raise ValueError("A porta não respondeu como BEATLIGHT-ESP32 BLP1.")
    if type(data.get("pixels")) is not int or data["pixels"]!=PIXELS or data.get("order")!="GRB" or data.get("pin")!=18 or data.get("watchdog_ms")!=750:
        raise ValueError("Use o firmware para WROOM-32, GPIO 18, GRB e 300 pixels.")
    if not isinstance(data.get("firmware"),str) or len(data["firmware"])>32:
        raise ValueError("Versão de firmware inválida.")
    return data


@dataclass(frozen=True)
class OutputConfig:
    brightness: int=64
    milliamps: int=2000

    def __post_init__(self):
        if type(self.brightness) is not int or not 0<=self.brightness<=255:
            raise ValueError("Brilho físico precisa estar entre 0 e 255.")
        if type(self.milliamps) is not int or not 500<=self.milliamps<=20000:
            raise ValueError("Limite estimado precisa estar entre 500 e 20.000 mA.")

    def payload(self):
        return struct.pack("<HBH",PIXELS,self.brightness,self.milliamps)


def rgb_payload(frame,strip_id):
    if not isinstance(frame,dict) or frame.get("id")!=strip_id or frame.get("profile")!="ws2812" or frame.get("model")!="RGB" or frame.get("pixels")!=PIXELS or frame.get("leds")!=PIXELS:
        raise ValueError("Prepare a fita escolhida como WS2812, 300 LEDs e 300 pixels.")
    data=frame.get("data")
    if not isinstance(data,list) or len(data)!=MAX_PAYLOAD or any(type(v) is not int or not 0<=v<=255 for v in data):
        raise ValueError("Quadro WS2812 precisa de exatamente 900 canais RGB inteiros.")
    return bytes(data)
