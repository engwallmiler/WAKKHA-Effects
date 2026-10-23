from dataclasses import dataclass, field
import math
from beatlight.lighting.patterns import MOTIFS
from beatlight.lighting.movers import MOVER_STYLES
from beatlight.lighting.breakdown import BREAKDOWN_STYLES

PALETTES = {
    "mint_blue": ((0.25, 1.0, 0.7), (0.2, 0.45, 1.0)),
    "amber_violet": ((1.0, 0.55, 0.08), (0.6, 0.15, 1.0)),
    "red_blue": ((1.0, 0.08, 0.12), (0.08, 0.3, 1.0)),
    "cyan_magenta": ((0.0, 1.0, 1.0), (1.0, 0.0, 0.7)),
    "lime_rose": ((0.45, 1.0, 0.0), (1.0, 0.1, 0.4)),
    "gold_ice": ((1.0, 0.65, 0.12), (0.45, 0.8, 1.0)),
    "white": ((1.0, 1.0, 1.0), (1.0, 1.0, 1.0)),
}
EFFECTS = ("kick_pulse", "beat_pulse", "beat_chase", "ambient", "musical", "bass_flow", "density_wash", "rhythmic_show", "orchestrated_show", "phrase_show")


@dataclass(frozen=True, slots=True)
class LightConfig:
    light_effect: str = "kick_pulse"
    light_master: float = 0.8
    light_pulse_ms: float = 240.0
    light_transition_ms: float = 300.0
    light_movement_speed: float = 0.4
    light_palette: str = "mint_blue"
    light_color_mode: str = "automatic"
    light_kick_weight: float = 0.7
    light_bass_weight: float = 0.65
    light_density_weight: float = 0.5
    light_white_strength: float = 1.0
    light_show_complexity: float = 0.7
    light_change_sensitivity: float = 1.0
    light_mover_pattern: str = "auto"
    light_breakdown_style: str = "auto"
    light_phrase_pattern: str = "auto"
    light_phrase_variation: str = "texture"
    light_phrase_prepare: str = "fade"
    light_phrase_prepare_ms: float = 140.0

    def __post_init__(self):
        if self.light_effect not in EFFECTS or self.light_palette not in PALETTES:
            raise ValueError("Efeito ou paleta de iluminação inválidos.")
        if self.light_color_mode not in ("fixed", "automatic"):
            raise ValueError("Perfil de cores inválido.")
        for key in ("light_master", "light_pulse_ms", "light_transition_ms", "light_movement_speed", "light_kick_weight", "light_bass_weight", "light_density_weight", "light_white_strength", "light_show_complexity", "light_phrase_prepare_ms", "light_change_sensitivity"):
            value = getattr(self, key)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("Parâmetros de iluminação devem ser números finitos.")
        if not 0 <= self.light_master <= 1 or not 0 <= self.light_movement_speed <= 1:
            raise ValueError("Master e velocidade de iluminação devem estar entre 0 e 1.")
        if any(not 0 <= getattr(self, key) <= 1 for key in ("light_kick_weight", "light_bass_weight", "light_density_weight")):
            raise ValueError("Pesos musicais devem estar entre 0 e 1.")
        if not 0 <= self.light_white_strength <= 1 or not 0 <= self.light_show_complexity <= 1:
            raise ValueError("Branco e complexidade devem estar entre 0 e 1.")
        if not .5 <= self.light_change_sensitivity <= 2:
            raise ValueError("Sensibilidade de mudança deve estar entre 0,5 e 2.")
        if self.light_mover_pattern not in ("auto",*MOVER_STYLES) or self.light_breakdown_style not in ("auto",*BREAKDOWN_STYLES):
            raise ValueError("Ritmo dos moves ou estilo de breakdown inválido.")
        if self.light_phrase_pattern not in ("auto", *MOTIFS):
            raise ValueError("Padrão cíclico inválido.")
        if self.light_phrase_variation not in ("texture", "cycle", "two_cycles"):
            raise ValueError("Variação dos ciclos inválida.")
        if self.light_phrase_prepare not in ("fade", "blackout", "none") or not 40 <= self.light_phrase_prepare_ms <= 300:
            raise ValueError("Preparação do ciclo inválida.")
        if not 80 <= self.light_pulse_ms <= 1000:
            raise ValueError("Pulso deve durar entre 80 e 1000 ms.")
        if not 0 <= self.light_transition_ms <= 3000:
            raise ValueError("Transição deve estar entre 0 e 3000 ms.")


@dataclass(frozen=True, slots=True)
class LightingControls:
    config: LightConfig = field(default_factory=LightConfig)
    armed: bool = False
    blackout: bool = False
    manual: bool = False
    manual_intensity: float = 0.7
    manual_pan: float = 0.5
    manual_tilt: float = 0.5
    manual_rgbw: bool = False
    manual_red: float = 0.25
    manual_green: float = 1.0
    manual_blue: float = 0.7
    manual_white: float = 0.0
    phrase_sync_id: int = 0
    phrase_sync_at: float | None = None

    def __post_init__(self):
        if not isinstance(self.config, LightConfig):
            raise ValueError("Configuração de iluminação inválida.")
        if any(type(v) is not bool for v in (self.armed, self.blackout, self.manual, self.manual_rgbw)):
            raise ValueError("Estados operacionais de iluminação devem ser booleanos.")
        if type(self.phrase_sync_id) is not int or self.phrase_sync_id < 0:
            raise ValueError("Identificador de sincronização inválido.")
        if self.phrase_sync_at is not None and (type(self.phrase_sync_at) not in (float, int)
                or not math.isfinite(self.phrase_sync_at) or self.phrase_sync_at < 0):
            raise ValueError("Instante de sincronização inválido.")
        for v in (self.manual_intensity, self.manual_pan, self.manual_tilt, self.manual_red, self.manual_green, self.manual_blue, self.manual_white):
            if type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1:
                raise ValueError("Valores manuais devem estar entre 0 e 1.")
