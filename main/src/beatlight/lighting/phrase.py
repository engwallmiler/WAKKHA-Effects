"""Ciclos de oito tempos com desenhos e articulações repetíveis."""
from dataclasses import dataclass
import math
from beatlight.lighting.patterns import (MOTIFS, MOTIF_NAMES, BANK, RHYTHMS,
    RHYTHM_NAMES, PatternPicker, slots_for)
from beatlight.lighting.novelty import TextureChange


@dataclass(frozen=True, slots=True)
class PhraseFrame:
    levels: tuple[float, ...]
    mover_levels: tuple[float, ...]
    colors: tuple[tuple[float, float, float], ...]
    gain: float
    pattern: str
    step: int
    cycle: int
    phase: float
    pending: bool
    preparation: bool
    novelty: float
    changes: int
    repetition: int
    masks: tuple[int, ...]
    rhythm: str
    change_reason: str


class PhraseSequencer:
    def __init__(self):
        self.reset()

    def reset(self):
        self._at = None
        self._last_cycle = self._palette = self._choice = None
        self._index = 0
        self._pending = False
        self._cooldown = -math.inf
        self._changes = 0
        self._initialized = False
        self._completed = 0
        self._cycle_full = False
        self._change = TextureChange()
        self._picker = PatternPicker()
        self._reason = ""

    def realign(self):
        self._last_cycle = None
        self._cooldown = -math.inf
        self._completed = 0
        self._cycle_full = False
        self._pending = False
        self._reason = ""

    def render(self, *, at, position, period, texture, cfg, palette, state, kick=0.0):
        if self._at is not None and at-self._at > .6:
            self.reset()
        self._at = at
        cycle = math.floor((position+1e-7)/8)
        whole = math.floor(position+1e-7)
        step, phase = whole%8, max(0.0,min(1.0,position-whole))
        allowed = state in ("warming","groove") and cfg.light_phrase_pattern=="auto"
        choice = (cfg.light_phrase_pattern,cfg.light_phrase_variation)
        if self._choice != choice:
            self._choice = choice
            self._pending = False
            self._completed = 0
            self._cycle_full = False
            self._last_cycle = None
        changed = self._change.observe(texture,period,cfg.light_change_sensitivity)
        if changed and allowed and not self._pending and position >= self._cooldown:
            self._pending = True
            self._reason = self._change.reason
            self._cooldown = (math.floor(position/8)+2)*8
        if cfg.light_phrase_pattern != "auto":
            self._pending = False
        if not self._initialized:
            self._initialized = True
            density = texture.density if texture else 0.0
            self._index = BANK.index("double" if density>.6 else "chase")
        if self._last_cycle is None:
            self._cycle_full = step==0 and phase<.1
            self._last_cycle, self._palette = cycle,palette
        elif cycle > self._last_cycle:
            if self._cycle_full and allowed:
                self._completed += 1
            limit = {"cycle":1,"two_cycles":2}.get(cfg.light_phrase_variation)
            periodic = allowed and limit is not None and self._completed>=limit
            if cfg.light_phrase_pattern=="auto" and (self._pending or periodic):
                current = BANK[self._index]
                self._index = BANK.index(self._picker.choose(current,cfg.light_show_complexity))
                self._changes += 1
                self._completed = 0
                if not self._pending:
                    self._reason = "programação de ciclos"
                self._pending = False
                self._change.accept()
            self._cycle_full = allowed
            self._palette, self._last_cycle = palette,cycle
        pattern = BANK[self._index] if cfg.light_phrase_pattern=="auto" else cfg.light_phrase_pattern
        slots = slots_for(pattern)
        slot = math.floor((step+phase)*2+1e-7)%16
        mask = slots[slot] if pattern in RHYTHMS else MOTIFS[pattern][step]
        density = texture.density*cfg.light_density_weight if texture else 0.0
        bass = texture.bass_level*cfg.light_bass_weight if texture else 0.0
        duty = .98 if step==7 and cfg.light_phrase_prepare!="none" else .58+.2*density
        articulation = phase*2%1 if pattern in RHYTHMS else phase
        if pattern=="staccato":
            duty = .35
        elif pattern in ("unison","wave","sweep"):
            duty = max(.75,duty)
        gate = max(0.0,1-articulation/duty)**.65
        accents = (1.0,.78,.92,.65,.95,.72,.85,.6)
        peak = min(1.0,(.95 if step==0 else .7)+.2*bass+.2*density)*accents[step]
        levels = [min(1.0,.015+peak*gate+.22*kick*cfg.light_kick_weight) if mask&(1<<i) else .01 for i in range(4)]
        # O início do ciclo tem uma assinatura coletiva, mesmo em motivos de pares
        # ou contratempos. Os outros sete tempos preservam o desenho escolhido.
        marker = .9*max(0.0,1-phase/.28) if step==0 else 0.0
        levels = tuple(max(v,marker) for v in levels)
        mover_gate = max(0.0,1-phase/(.98 if step==7 else .7))**.65
        movers = (min(1.0,max(marker,.02+peak*mover_gate)),)*2
        colors = tuple(self._palette[(i+step//2)%2] for i in range(4))
        window = min(cfg.light_phrase_prepare_ms/1000,period*.4)
        remaining = (8-(step+phase))*period
        preparation = state in ("warming","groove") and cfg.light_phrase_prepare!="none" and 0<remaining<=window
        gain = (0.0 if cfg.light_phrase_prepare=="blackout" else max(0.0,min(1.0,remaining/window))**2) if preparation else 1.0
        visible_slots = (15,*slots[1:])
        return PhraseFrame(levels,movers,colors,gain,pattern,step+1,cycle+1,phase,self._pending,
            preparation,self._change.score,self._changes,self._completed+1,visible_slots,
            RHYTHM_NAMES[pattern],self._reason)
