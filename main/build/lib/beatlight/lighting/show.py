"""Sequenciador de PARs: padrões relativos de oito tempos e viradas por textura.

Consome descritores já calculados. Não detecta instrumentos ou downbeats;
a grade local pode continuar sem kicks. Variações estruturais são sorteadas
apenas em fronteiras musicais, preservando o relógio e os acentos do drop.
"""
from dataclasses import dataclass
from random import Random
import math
from colorsys import rgb_to_hsv, hsv_to_rgb

# Máscaras dos quatro PARs, uma entrada por tempo. Sempre repetem em oito.
PATTERNS = {
    "chase": (1, 2, 4, 8, 1, 2, 4, 8),
    "bounce": (1, 2, 4, 8, 4, 2, 1, 2),
    "pairs": (5, 10, 5, 10, 5, 10, 5, 10),
    "mirror": (9, 6, 9, 6, 9, 6, 9, 6),
    "sweep": (1, 3, 7, 15, 8, 12, 14, 15),
    "response": (5, 2, 10, 8, 5, 1, 10, 4),
    "cross": (3, 12, 5, 10, 9, 6, 5, 10),
    "wave": (1, 3, 6, 12, 8, 12, 6, 3),
    "question": (1, 2, 3, 0, 8, 4, 12, 15),
    "double": (1, 4, 2, 8, 5, 10, 9, 6),
}
NAMES = {"cross": "Cruzamento", "wave": "Onda", "question": "Pergunta e resposta", "double": "Perseguição dupla", "chase": "Perseguição", "bounce": "Vai e volta", "pairs": "Pares alternados",
    "mirror": "Espelho", "sweep": "Acumulação", "response": "Resposta do baixo",
    "breakdown": "Tensão espaçada", "buildup": "Escalada", "drop": "Impacto pós-drop",
    "fill": "Virada · novas camadas", "acquiring": "Resposta ao áudio · adquirindo grade"}


BUILD_SCENES = (
    ("Escada crescente", (1,2,4,8,3,6,12,15)),
    ("Cruzamentos", (9,6,3,12,5,10,7,14)),
    ("Ondas", (1,3,6,12,8,12,6,3)),
    ("Chamadas coletivas", (5,10,9,6,15,6,9,15)),
)
DROP_SCENES = (
    ("Impactos em cascata", (15,1,4,8,15,2,9,6)),
    ("Impactos cruzados", (15,9,6,3,15,12,5,10)),
    ("Resposta dupla", (15,5,10,9,15,10,5,6)),
    ("Abertura e resposta", (15,3,12,6,15,9,1,8)),
)


@dataclass(frozen=True, slots=True)
class ShowFrame:
    levels: tuple[float, ...]
    colors: tuple[tuple[float, float, float], ...]
    pattern: str
    step: int
    fills: int
    novelty: float
    whites: tuple[float, ...] = (0.0, 0.0, 0.0, 0.0)
    rhythm: str = ""
    masks: tuple[int, ...] = ()
    phase: float = 0.0


class ShowSequencer:
    def __init__(self):
        self.reset()

    def reset(self):
        self._at = None
        self._sample_at = None
        self._baseline = None
        self._novel_since = None
        self._novelty = 0.0
        self._pending_fill = None
        self._fill_until = -math.inf
        self._cooldown = -math.inf
        self._fills = 0
        self._pattern = "chase"
        self._bar = None
        self._last_position = None
        self._palette = None
        self._color_key = None
        self._variation = 0
        self._state = None
        self._family = "sparse"
        self._grid_revision = None
        self._origin = None
        self._subdivision = 1
        self._scene_random = Random(23)
        self._scene_key = None
        self._scene_index = 0

    def _observe(self, texture, at, position, cfg, allow_fill):
        if texture is None or texture.updated_at == self._sample_at:
            return
        values = (texture.density * cfg.light_density_weight,
                  min(1.0, texture.onset_rate / 10) * cfg.light_density_weight,
                  texture.bass_level * cfg.light_bass_weight, texture.brightness * cfg.light_density_weight)
        dt = max(0.0, texture.updated_at - self._sample_at) if self._sample_at is not None else 0.0
        self._sample_at = texture.updated_at
        if self._baseline is None:
            self._baseline = values
            return
        # Compare com o leito de alguns segundos; não conte cada ataque como nova camada.
        rise = tuple(max(0.0, a - b) for a, b in zip(values, self._baseline))
        self._novelty = min(1.0, max(rise[0] / .13, rise[1] / .18,
                                   rise[2] / .22, rise[3] / .15))
        if self._novelty >= 1.0:
            if self._novel_since is None:
                self._novel_since = at
            if (allow_fill and at - self._novel_since >= .15 and position is not None
                    and position >= self._cooldown and self._pending_fill is None):
                self._pending_fill = math.floor(position) + 1
                self._cooldown = self._pending_fill + 8
        else:
            self._novel_since = None
        mix = 1 - math.exp(-min(dt, .5) / 3.0)
        self._baseline = tuple(b + (a - b) * mix for a, b in zip(values, self._baseline))

    def render(self, *, at, beat, structure, texture, cfg, palette, kick=0.0, layered=False, position_override=None):
        valid = bool(beat and beat.period and beat.state in ("locked", "coasting") and beat.confidence >= .35)
        position = (position_override if position_override is not None else beat.beat_index+beat.phase) if valid else None
        # Uma nova fonte, uma interrupção ou uma correção que recua a grade não
        # podem reaplicar uma virada pendente da sessão anterior.
        if (self._at is not None and at - self._at > .6) or (
                position is not None and self._last_position is not None and position < self._last_position - .25):
            self.reset()
        self._at = at
        self._last_position = position
        self._observe(texture, at, position, cfg, structure.state in ("warming", "groove"))
        density = texture.density * cfg.light_density_weight if texture else 0.0
        bass = texture.bass_level * cfg.light_bass_weight if texture else 0.0
        activity = texture.bass_activity * cfg.light_bass_weight if texture else 0.0
        state, tension = structure.state, structure.tension
        if position is None:
            # Sem grade não invente um BPM. Graves e kicks ainda fazem os PARs reagirem.
            levels = tuple(min(1.0, .04 + bass * (.3 if i % 2 else .65)
                               + activity * (.65 if i % 2 else .2) + kick * cfg.light_kick_weight)
                           for i in range(4))
            return ShowFrame(levels, tuple(palette[i % 2] for i in range(4)), "acquiring", 0, self._fills, self._novelty)
        # Respeite a origem relativa da frase, inclusive o reinício no drop.
        origin = structure.grid.phrase_origin if structure.grid else 0
        revision = structure.grid.revision if structure.grid else None
        if origin != self._origin or revision != self._grid_revision:
            self._pending_fill = None
            self._fill_until = -math.inf
            self._bar = None
        self._origin, self._grid_revision = origin, revision
        relative = position - origin
        step, phase = math.floor(relative) % 8, relative % 1
        bar = math.floor(relative / 4)
        color_key = (cfg.light_palette, cfg.light_color_mode)
        if self._palette is None or bar != self._bar or state != self._state or color_key != self._color_key:
            self._palette = palette
        self._color_key = color_key
        if bar != self._bar:
            # A mesma família se mantém no mínimo quatro tempos. Sem rotação aleatória.
            if density > (.27 if self._family == "dense" else .32):
                self._family = "dense"
                bank = ("pairs", "mirror", "sweep")
            elif bass > (.26 if self._family == "bass" else .32) and activity > .08:
                self._family = "bass"
                bank = ("response", "bounce")
            else:
                self._family = "sparse"
                bank = ("chase", "bounce")
            if layered:
                bank = ({"dense": ("pairs", "mirror", "cross", "wave", "sweep"),
                         "bass": ("response", "question", "double", "bounce"),
                         "sparse": ("chase", "bounce", "question")})[self._family]
            evolution = math.floor(relative / 16) if layered and cfg.light_show_complexity >= .35 else 0
            self._pattern = bank[(self._variation + evolution) % len(bank)]
            self._subdivision = 2 if layered and cfg.light_show_complexity > .6 and density > .3 else 1
        self._bar, self._state = bar, state
        if state not in ("warming", "groove"):
            self._pending_fill = None
            self._fill_until = -math.inf
        if self._pending_fill is not None and position >= self._pending_fill:
            if position < self._pending_fill + 2:
                self._fill_until = self._pending_fill + 2
                self._fills += 1
                self._variation += 1
            self._pending_fill = None
        scene_key = (state, origin, revision, math.floor(relative/8) if state=="buildup" else 0)
        if state in ("buildup","drop") and scene_key != self._scene_key:
            options = [i for i in range(4) if self._scene_key is None or i!=self._scene_index]
            self._scene_index = self._scene_random.choice(options)
        self._scene_key = scene_key
        rhythm = "Colcheias" if self._subdivision==2 else "Batidas"
        echo_mask = 0
        preview = ()
        pattern = self._pattern
        mask = PATTERNS[pattern][math.floor(relative * self._subdivision) % 8]
        pulse_phase = (relative * self._subdivision) % 1
        duty = .5 + .25 * min(1.0, density / .5)
        peak = min(1.0, .55 + .35 * density + .2 * bass)
        floor = .015 + .025 * density
        if state == "breakdown":
            pattern = "breakdown"
            scene = (9,0,6,0,9,0,6,0)
            mask = scene[step]
            rhythm = "Tensão espaçada"
            preview = tuple(v for value in scene for v in (value,0))
            peak, duty, floor = .22 + .28 * tension, .65, .01
        elif state == "buildup":
            pattern = "buildup"
            subdivisions = 2 if tension > .55 or structure.roll_rate > 5 else 1
            substep = math.floor(relative * subdivisions)
            rhythm, scene = BUILD_SCENES[self._scene_index]
            mask = scene[substep%8]
            pulse_phase = (relative*subdivisions)%1
            peak, duty, floor = .45+.5*tension, .52+.13*(self._scene_index%2), .025+.04*tension
            preview = tuple(scene[i%8] if subdivisions==2 else (scene[i//2] if i%2==0 else 0) for i in range(16))
        elif state == "drop":
            pattern = "drop"
            rhythm, scene = DROP_SCENES[self._scene_index]
            mask = scene[step]
            echo_mask = scene[(step+3)%8] if self._scene_index in (1,2) and step%2 else 0
            preview = tuple(scene[i//2] if i%2==0 else
                (scene[(i//2+3)%8] if self._scene_index in (1,2) and i//2%2 else 0) for i in range(16))
            # Drop não herda os dois passos/tempo do groove denso.
            pulse_phase = phase
            peak, duty, floor = 1.0, .78, .10
        elif position < self._fill_until:
            pattern = "fill"
            mask = (1, 4, 2, 8)[math.floor(relative * 2) % 4]
            pulse_phase, peak, duty = (relative * 2) % 1, .95, .7
            rhythm = "Virada em colcheias"
            preview = (1,4,2,8)*4
        gate = max(0.0, 1 - pulse_phase / duty) ** .65
        # Um contratempo espacial usa o baixo e a densidade. Não transforma baixo em kick.
        off_gate = max(0.0, 1 - abs(phase - .55) / .22)
        off_level = min(.65, .35 * bass + .55 * activity + .25 * density)
        levels, colors, whites = [], [], []
        for i in range(4):
            active = bool(mask & (1 << i))
            primary = peak * gate + kick * cfg.light_kick_weight * .3 if active else 0.0
            secondary = off_gate * off_level if not active and state not in ("breakdown", "buildup") else 0.0
            echo = .5*max(0.0,1-abs(phase-.58)/.18) if echo_mask&(1<<i) else 0.0
            levels.append(min(1.0, floor + max(primary, secondary, echo)))
            # Acento branco independente: apenas no conjunto ativo, com dimmer comum.
            accent_white = (cfg.light_white_strength * cfg.light_show_complexity * kick *
                            (.6 if state == "drop" else .25)) if layered and active and cfg.light_color_mode == "automatic" else 0.0
            whites.append(accent_white)
            # Trocas de cor em tempos inteiros, repetindo a frase de oito tempos.
            color = self._palette[(i + step // 2 + (1 if pattern == "fill" else 0)) % 2]
            if layered and cfg.light_color_mode == "automatic" and state in ("warming", "groove", "drop"):
                hue, saturation, value = rgb_to_hsv(*color)
                turn = ((math.floor(relative / 2) % 8) / 8 + i / 12) * cfg.light_show_complexity
                color = hsv_to_rgb((hue + turn + self._variation * .07) % 1, max(.7, saturation), value)
            white = (.25 + .72 * tension if state == "buildup" else
                     .65 * kick if state == "drop" else 0.0) if cfg.light_color_mode == "automatic" else 0.0
            colors.append(tuple(c + (1 - c) * min(1.0, white) for c in color))
        if not preview:
            preview = tuple(PATTERNS[self._pattern][(i*self._subdivision//2)%8] if self._subdivision==2 or i%2==0 else 0 for i in range(16))
        return ShowFrame(tuple(levels), tuple(colors), pattern, step+1, self._fills, self._novelty,
            tuple(whites),rhythm,preview,phase)
