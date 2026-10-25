"""Ritmo e cor comuns ao par de moving heads; não calcula pan/tilt."""
from dataclasses import dataclass
from colorsys import rgb_to_hsv,hsv_to_rgb
from random import Random
import math

MOVER_STYLES={"pulse":"Pulso com acentos","double":"Pulso duplo","offbeat":"Resposta no contratempo",
    "hold":"Sustentação de quatro tempos","swell":"Ondas de oito tempos","syncopated":"Síncope conjunta",
    "bass":"Respiração do baixo","gates":"Cortes e sustentação"}


@dataclass(frozen=True,slots=True)
class MoverFrame:
    level:float
    color:tuple[float,...]
    white:float
    rhythm:str


class MoverSequencer:
    def __init__(self):
        self.reset()

    def reset(self):
        self._key=None
        self._style="double"
        self._rng=Random(51)

    def render(self, *, position,texture,cfg,palette,key):
        choice=(cfg.light_mover_pattern,key)
        if choice!=self._key:
            if cfg.light_mover_pattern=="auto":
                options=[k for k in MOVER_STYLES if k!=self._style]
                self._style=self._rng.choice(options) if self._key is not None else ("double" if texture and texture.density>.55 else "hold")
            else:
                self._style=cfg.light_mover_pattern
            self._key=choice
        p=max(0.0,position or 0.0)%8
        step,phase=int(p),p%1
        bass=texture.bass_level*cfg.light_bass_weight if texture else 0.0
        activity=texture.bass_activity*cfg.light_bass_weight if texture else 0.0
        density=texture.density*cfg.light_density_weight if texture else 0.0
        env=lambda x,d:max(0.0,1-x/d)**.7
        if position is None:
            drive=.35+.5*bass+.15*activity
        elif self._style=="double":
            drive=env((p*2)%1,.68)*(1.0 if phase<.5 else .55)
        elif self._style=="offbeat":
            drive=.12+.88*env((phase+.5)%1,.7)
        elif self._style=="hold":
            drive=.4+.6*(.5+.5*math.sin(math.pi*p/2))
        elif self._style=="swell":
            drive=.2+.8*(.5-.5*math.cos(math.pi*p/4))
        elif self._style=="syncopated":
            slots=(1,0,0,.7,1,0,.5,0,1,.6,0,.8,1,0,.6,0)
            drive=.08+slots[int(p*2)]*env((p*2)%1,.72)
        elif self._style=="bass":
            drive=.2+.55*bass+.25*activity
        elif self._style=="gates":
            drive=(1,.3,.85,.55,1,.7,.4,.85)[step]*env(phase,.95 if step in (0,3,4,7) else .4)
        else:
            drive=env(phase,.75)*(1,.7,.85,.65,.95,.7,.8,.55)[step]
        level=min(1.0,.06+drive*(.7+.25*bass+.2*density))
        if position is not None and step==0:
            level=max(level,.95*max(0.0,1-phase/.28))
        base=palette[(step//2)%2]
        white=0.0
        if cfg.light_color_mode=="automatic":
            h,s,v=rgb_to_hsv(*base)
            turn=(step//2)*.14+list(MOVER_STYLES).index(self._style)*.035
            color=hsv_to_rgb((h+turn)%1,max(.7,s),v)
            white=cfg.light_white_strength*(.15 if step in (0,4) else .04)*drive
        else:
            color=base
        return MoverFrame(level,color,white,MOVER_STYLES[self._style])
