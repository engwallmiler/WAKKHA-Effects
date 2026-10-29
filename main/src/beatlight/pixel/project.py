"""Projetos do Pixel Studio separados das preferências de áudio/DMX."""
import json
import math
import os
from pathlib import Path
import tempfile
from beatlight.pixel.topology import validate_patch,validate_exact_copies

EFFECTS={"inherit","ambient","pulse","chase","mirror","wave","helix","rain","drop","comet",
         "scanner","sparkle","meteor","fire","rainbow","blocks","bounce","ripple","equalizer","snake","aurora",
         "weave","orbit","shards","tide","lattice","vortex"}
PALETTES={"inherit","deep","fire","ice","acid","mono","red","green","blue","magenta","cyan","amber","primaries","neon","sunset","ocean"}
MAX_BYTES=500_000


def number(value,low,high):
    return type(value) in (int,float) and math.isfinite(value) and low<=value<=high


def validate_project(data):
    if not isinstance(data,dict) or type(data.get("version")) is not int or data["version"]!=1:
        raise ValueError("Versão de projeto Pixel Studio inválida.")
    geometry=data.get("geometry",{})
    lines=geometry.get("lines") if isinstance(geometry,dict) else None
    if not isinstance(geometry,dict) or geometry.get("version")!=1 or not isinstance(lines,list) or not 1<=len(lines)<=32:
        raise ValueError("Use de 1 a 32 linhas no projeto.")
    leds=pixels=0
    for line in lines:
        if not isinstance(line,dict) or not isinstance(line.get("name"),str) or not line["name"].strip() or len(line["name"])>48:
            raise ValueError("Nome de linha inválido.")
        a,b=line.get("start"),line.get("end")
        if any(not isinstance(p,dict) or not number(p.get("x"),0,1200) or not number(p.get("y"),0,560) for p in (a,b)):
            raise ValueError("Coordenadas de linha inválidas.")
        if math.hypot(a["x"]-b["x"],a["y"]-b["y"])<1 or not number(line.get("meters"),.001,1000):
            raise ValueError("Comprimento de linha inválido.")
        if type(line.get("leds")) is not int or not 1<=line["leds"]<=4096 or type(line.get("pixels")) is not int or not 1<=line["pixels"]<=min(2048,line["leds"]):
            raise ValueError("Resolução de linha inválida.")
        leds+=line["leds"]; pixels+=line["pixels"]
    if leds>32768 or pixels>8192:
        raise ValueError("Limite de LEDs/pixels do projeto excedido.")
    strips=data.get("strips")
    if not isinstance(strips,list) or len(strips)!=len(lines):
        raise ValueError("Cada linha precisa de seus controles de fita.")
    ids=set()
    for strip in strips:
        if not isinstance(strip,dict) or not isinstance(strip.get("id"),str) or not 1<=len(strip["id"])<=64 or strip["id"] in ids:
            raise ValueError("Identificador de fita inválido ou duplicado.")
        ids.add(strip["id"])
        if strip.get("effect") not in EFFECTS or strip.get("palette") not in PALETTES or strip.get("profile") not in ("inherit","ws2811","ws2812","rgbw"):
            raise ValueError("Efeito, paleta ou perfil da fita inválido.")
        if strip.get("response") not in ("hybrid","grid","kick","bass","density","ambient"):
            raise ValueError("Resposta musical da fita inválida.")
        if type(strip.get("enabled")) is not bool or type(strip.get("reverse")) is not bool:
            raise ValueError("Ativação ou sentido da fita inválido.")
        if not number(strip.get("brightness"),0,1) or not number(strip.get("speed"),.1,4) or not number(strip.get("phase"),0,1):
            raise ValueError("Brilho, velocidade ou fase da fita inválido.")
    if 'patch' in data:
        validate_patch(data['patch'],ids)
        validate_exact_copies(data['patch'],lines,strips)
    show=data.get("show",{})
    if not isinstance(show,dict) or len(show)>64:
        raise ValueError("Controles globais inválidos.")
    ranges={"bpm":(40,240),"brightness":(0,1),"speed":(.1,4),"trail":(0,1),"transition":(1,12),
            "variation":(0,1),"white":(0,1),"kickDepth":(0,1),"dropEnergy":(0,1),"strobeLevel":(0,1),"peakLevel":(0,1),"glow":(0,3)}
    choices={"palette":PALETTES-{"inherit"},"colorBehavior":{"scene","spectrum","beat","bar","solid"},
             "colorMode":{"rgb","rgbw"},"whiteTone":{"warm","neutral","cool"},"kickMode":{"beat","bar","off"},
             "dropStyle":{"impact","turbo","prism"},"strobeMode":{"drop","beat","bar"},"strobeColor":{"rgbw","rgb","white"},
             "meter":{3,4,6},"sceneBars":{1,2,4,8,16},"dropBars":{4,8,16},"dropRate":{1,2,4},
             "changeMode":{"bars","hybrid","elements","hold"},"morphBeats":{0,.5,1,2,4,8,16},
             "layerCount":{2,3,4},"peakMode":{"auto","on","off"},"peakEvery":{4,8},
             "compositionStyle":{"hypnotic","varied"},
             "mode":EFFECTS-{"inherit","dropseq"}|{"organic","auto"}}
    for key,value in show.items():
        if key in ranges:
            valid=number(value,*ranges[key])
        elif key in choices:
            valid=type(value) in (str,int,float) and value in choices[key]
        elif key in ("strobes","followStructure","progressive","energyMotion"):
            valid=type(value) is bool
        elif key=="solidColor":
            valid=isinstance(value,list) and len(value)==3 and all(type(v) is int and 0<=v<=255 for v in value)
        else:
            valid=False
        if not valid:
            raise ValueError(f"Controle global inválido: {key}.")
    return data


class PixelProjectStore:
    def __init__(self,path):
        self.path=Path(path)

    def load(self):
        if not self.path.exists():
            return None
        if self.path.stat().st_size>MAX_BYTES:
            raise ValueError("Projeto excede 500 KB.")
        return validate_project(json.loads(self.path.read_text(encoding="utf-8")))

    def save(self,data):
        validate_project(data)
        encoded=json.dumps(data,ensure_ascii=False,allow_nan=False,indent=2)
        if len(encoded.encode("utf-8"))>MAX_BYTES:
            raise ValueError("Projeto excede 500 KB.")
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temp=None
        try:
            with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=self.path.parent,suffix=".tmp",delete=False) as stream:
                temp=Path(stream.name); stream.write(encoded); stream.flush(); os.fsync(stream.fileno())
            os.replace(temp,self.path)
        finally:
            if temp and temp.exists():temp.unlink()
