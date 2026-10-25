"""Contrato pequeno entre a análise Python e o renderizador local de pixels.

O relógio e a previsão não são eventos acústicos. Nenhuma saída física é aberta.
"""
import math
from beatlight.music.grid import project_grid


def unit(value):
    return min(1.0,max(0.0,float(value))) if isinstance(value,(int,float)) and math.isfinite(value) else 0.0


def music_packet(snapshot,status,at):
    active = bool(snapshot and status.state=="running" and status.audio_age<.5
                  and 0<=at-snapshot.acquired_at<.6)
    structure = snapshot.structure if active and not snapshot.structure_error else None
    texture = snapshot.texture if active and not snapshot.texture_error else None
    clock = None
    if structure and structure.grid and structure.grid.state in ("tracking","predicting"):
        grid=project_grid(structure.grid,at)
        clock={"beat":grid.beat_index+grid.phase,"bpm":60/grid.period,
               "source":snapshot.timing_source,"confidence":grid.confidence}
    elif active and snapshot.beat and not snapshot.beat_error:
        beat=snapshot.beat
        if beat.state in ("locked","coasting") and beat.period>0 and 0<=at-beat.updated_at<.6:
            clock={"beat":beat.beat_index+beat.phase+(at-beat.updated_at)/beat.period,
                   "bpm":60/beat.period,"source":snapshot.timing_source,"confidence":beat.confidence}
    events=structure.confirmed_kicks if structure and not snapshot.kick_error else ()
    kick=max((e for e in events if e.occurred_at<=at),key=lambda e:e.occurred_at,default=None)
    audible=active and not snapshot.silent and not (structure and structure.state=="silence")
    return {"version":1,"at":at,"sent_at":at,"active":active,"audible":bool(audible),"clock":clock,
            "kick":{"id":kick.occurred_at,"age":at-kick.occurred_at,"strength":unit(kick.intensity)} if kick else None,
            "music":{"state":structure.state if structure else "warming",
                     "tension":unit(structure.tension) if structure else 0,
                     "energy":unit(structure.energy) if structure else 0,
                     "brightness":unit(structure.brightness) if structure else 0,
                     "drop_id":structure.drop_id if structure else 0,
                     "drop_kicks":structure.drop_kicks if structure else 0,
                     "bass":unit(texture.bass_level) if texture else 0,
                     "density":unit(texture.density) if texture else 0,
                     "activity":unit(texture.bass_activity) if texture else 0}}


def validate_frame(frame):
    """Valida RGB lógico de pixels endereçáveis, nunca LEDs físicos duplicados."""
    if not isinstance(frame,dict) or type(frame.get("version")) is not int or frame["version"]!=1 or frame.get("physical_output") is not False:
        raise ValueError("Quadro de pixels inválido.")
    strips=frame.get("strips")
    if not isinstance(strips,list) or not 1<=len(strips)<=32:
        raise ValueError("Quadro deve conter de 1 a 32 fitas.")
    total=0
    ids=set()
    for strip in strips:
        if not isinstance(strip,dict) or not isinstance(strip.get("id"),str) or strip["id"] in ids:
            raise ValueError("Identificador de fita inválido ou duplicado.")
        ids.add(strip["id"])
        count=strip.get("pixels")
        width=3 if strip.get("model")=="RGB" else 4 if strip.get("model")=="RGBW" else 0
        data=strip.get("data")
        if type(count) is not int or not 1<=count<=2048 or not width or not isinstance(data,list) or len(data)!=count*width:
            raise ValueError("Quantidade de canais da fita inválida.")
        if any(type(v) is not int or not 0<=v<=255 for v in data):
            raise ValueError("Canais devem ser inteiros entre 0 e 255.")
        if strip.get("profile") in ("ws2811","ws2812") and width!=3:
            raise ValueError("WS2811/WS2812 usam pixels RGB neste perfil.")
        total+=count
    if total>8192:
        raise ValueError("Limite de 8.192 pixels excedido.")
    return frame
