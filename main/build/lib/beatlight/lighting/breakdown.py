"""Luz sustentada para pads/melodias calmas, independente do grid."""
from dataclasses import dataclass
from colorsys import rgb_to_hsv,hsv_to_rgb
import math

BREAKDOWN_STYLES={"breathing":"Respiração lenta","aurora":"Aurora de cores",
    "crossfade":"Passagem suave","glow":"Brilho sustentado"}


@dataclass(frozen=True,slots=True)
class CalmFrame:
    levels:tuple[float,...]
    colors:tuple[tuple[float,...],...]
    amount:float
    style:str


class BreakdownWash:
    def __init__(self):
        self.reset()

    def reset(self):
        self._at=None
        self._cycles=0.0
        self._calm=False
        self._amount=0.0
        self._entry=0
        self._active=False
        self._style="aurora"

    def render(self, *, at,structure,cfg,palette):
        if self._at is not None and at-self._at>.6:
            self.reset()
        dt=min(.1,max(0.0,at-self._at)) if self._at is not None else 0.0
        self._at=at
        active=structure.state=="breakdown"
        if not active:
            self._active=False
            self._amount=0.0
            self._calm=False
            return None
        if not self._active:
            self._entry+=1
            self._style=tuple(BREAKDOWN_STYLES)[self._entry%4]
            self._calm=structure.tension<.45 and structure.energy<.65 and structure.roll_strength<.25
            self._amount=1.0 if self._calm else 0.0
        self._active=True
        if structure.tension<.38 and structure.energy<.6 and structure.roll_strength<.2:
            self._calm=True
        elif structure.tension>.52 or structure.energy>.75 or structure.roll_strength>.35:
            self._calm=False
        self._amount+=(float(self._calm)-self._amount)*(1-math.exp(-dt/.65))
        duration=max(6.0,14-7*structure.tension-2*structure.energy)
        self._cycles=(self._cycles+dt/duration)%4
        style=self._style if cfg.light_breakdown_style=="auto" else cfg.light_breakdown_style
        levels,colors=[],[]
        for i in range(4):
            offset=0.0 if style in ("breathing","glow") else i/4
            wave=.5-.5*math.cos(2*math.pi*(self._cycles+offset))
            drive=.8+.2*wave if style=="glow" else .25+.75*wave
            level=(.08+.2*drive+.12*structure.energy)*(.75+.25*structure.tension)
            levels.append(min(.45,level))
            if cfg.light_color_mode=="automatic":
                a,b=(rgb_to_hsv(*c) for c in palette)
                mix=.5+.5*math.sin(2*math.pi*(self._cycles/2+i/8))
                hue=(a[0]+((b[0]-a[0]+.5)%1-.5)*mix+.04*math.sin(2*math.pi*self._cycles))%1
                colors.append(hsv_to_rgb(hue,max(.4,a[1]*(1-mix)+b[1]*mix),1.0))
            else:
                colors.append(palette[i%2])
        return CalmFrame(tuple(levels),tuple(colors),self._amount,BREAKDOWN_STYLES[style])
