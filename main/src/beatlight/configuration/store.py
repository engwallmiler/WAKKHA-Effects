"""Preferências versionadas, validação e gravação atômica em JSON."""
from dataclasses import asdict, dataclass
import json
import logging
import math
import os
from pathlib import Path
import tempfile
from beatlight.dsp.config import DspConfig
from beatlight.dsp.kick_config import KickConfig
from beatlight.music.config import BeatConfig
from beatlight.lighting.config import LightConfig

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Settings:
    version: int = 13
    source: str = "wasapi"
    device_id: str = ""
    block_size: int = 512
    queue_capacity: int = 8
    silence_db: float = -65.0
    ui_fps: int = 30
    sync_source: str = "audio"
    link_offset_ms: float = 0.0
    fft_size: int = 2048
    fft_overlap: int = 75
    remove_dc: bool = True
    filter_mode: str = "none"
    filter_low_hz: float = 40.0
    filter_high_hz: float = 150.0
    low_mid_hz: float = 250.0
    mid_high_hz: float = 2000.0

    kick_low_hz: float = 40.0
    kick_high_hz: float = 150.0
    kick_sensitivity: float = 1.0
    kick_refractory_ms: float = 180.0
    kick_floor_db: float = -60.0

    beat_min_bpm: float = 90.0
    beat_max_bpm: float = 160.0
    beat_hold_seconds: float = 4.0

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

    def light_config(self) -> LightConfig:
        return LightConfig(**{field: getattr(self, field) for field in LightConfig.__dataclass_fields__})

    def beat_config(self) -> BeatConfig:
        return BeatConfig(**{field: getattr(self, field) for field in BeatConfig.__dataclass_fields__})

    def kick_config(self) -> KickConfig:
        return KickConfig(**{field: getattr(self, field) for field in KickConfig.__dataclass_fields__})

    def dsp_config(self) -> DspConfig:
        return DspConfig(**{field: getattr(self, field) for field in DspConfig.__dataclass_fields__})



def validate(data: dict) -> Settings:
    if not isinstance(data, dict) or type(data.get("version", 1)) is not int or data.get("version", 1) not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13):
        raise ValueError("Formato de configuração não suportado.")
    migrated = {k: v for k, v in data.items() if k in Settings.__dataclass_fields__}
    if data.get("version", 1) == 1:
        for field in DspConfig.__dataclass_fields__:
            migrated.pop(field, None)  # campos desconhecidos de v1 não viram ajustes DSP implícitos
    if data.get("version", 1) < 3:
        for field in KickConfig.__dataclass_fields__:
            migrated.pop(field, None)
    if data.get("version", 1) < 4:
        for field in BeatConfig.__dataclass_fields__:
            migrated.pop(field, None)
    if data.get("version", 1) < 5:
        for field in LightConfig.__dataclass_fields__:
            migrated.pop(field, None)
    if data.get("version", 1) < 6:
        migrated.pop("light_color_mode", None)
    if data.get("version", 1) < 7:
        for field in ("light_kick_weight", "light_bass_weight", "light_density_weight"):
            migrated.pop(field, None)
    if data.get("version", 1) < 8:
        migrated.pop("light_white_strength", None)
        migrated.pop("light_show_complexity", None)
    if data.get("version", 1) < 9:
        for field in ("light_phrase_pattern", "light_phrase_prepare", "light_phrase_prepare_ms"):
            migrated.pop(field, None)
    if data.get("version", 1) < 10:
        migrated.pop("light_phrase_variation", None)
    if data.get("version", 1) < 11:
        migrated.pop("light_change_sensitivity", None)
    if data.get("version", 1) < 12:
        migrated.pop("light_mover_pattern", None)
        migrated.pop("light_breakdown_style", None)
    if data.get("version", 1) < 13:
        migrated.pop("sync_source", None)
        migrated.pop("link_offset_ms", None)
    migrated["version"] = 13  # Mantém os campos conhecidos de cada versão anterior.
    settings = Settings(**migrated)
    if settings.source not in ("wasapi", "synthetic", "structure_demo", "texture_demo"):
        raise ValueError("Fonte de áudio inválida.")
    if not isinstance(settings.device_id, str):
        raise ValueError("Identificador de dispositivo inválido.")
    if type(settings.block_size) is not int or settings.block_size not in (256, 512, 1024, 2048):
        raise ValueError("Tamanho de bloco inválido.")
    if type(settings.queue_capacity) is not int or not 2 <= settings.queue_capacity <= 64:
        raise ValueError("Capacidade da fila inválida.")
    if type(settings.silence_db) not in (int, float) or not math.isfinite(settings.silence_db) or not -100 <= settings.silence_db <= -20:
        raise ValueError("Limiar de silêncio inválido.")
    if type(settings.ui_fps) is not int or not 15 <= settings.ui_fps <= 60:
        raise ValueError("Taxa de atualização inválida.")
    if settings.sync_source not in ("audio", "link"):
        raise ValueError("Fonte de sincronismo inválida.")
    if (type(settings.link_offset_ms) not in (int, float) or not math.isfinite(settings.link_offset_ms)
            or not -250 <= settings.link_offset_ms <= 250):
        raise ValueError("Compensação Link inválida.")
    settings.dsp_config()
    settings.kick_config()
    settings.beat_config()
    settings.light_config()
    return settings


class SettingsStore:
    def __init__(self, path: Path):
        self.path = path
        self.warning = ""

    def load(self) -> Settings:
        try:
            return validate(json.loads(self.path.read_text(encoding="utf-8")))
        except FileNotFoundError:
            return Settings()
        except (ValueError, TypeError, OSError) as exc:
            self.warning = f"Preferências inválidas; usando valores padrão: {exc}"
            log.warning("settings_fallback", extra={"reason": str(exc)})
            return Settings()

    def save(self, settings: Settings) -> None:
        self.export(self.path, settings)

    @staticmethod
    def export(path: Path, settings: Settings) -> None:
        validate(asdict(settings))
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                             suffix=".tmp", delete=False) as stream:
                temp_path = Path(stream.name)
                json.dump(asdict(settings), stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, path)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()

    @staticmethod
    def import_file(path: Path) -> Settings:
        return validate(json.loads(path.read_text(encoding="utf-8")))
