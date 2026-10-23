"""Contratos públicos; nenhuma dependência de Qt, PortAudio ou protocolos DMX."""
from dataclasses import dataclass
import math
from typing import Callable, Protocol
import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class AudioDevice:
    id: str
    name: str
    sample_rate: int
    channels: int
    is_default: bool = False
    backend: str = "WASAPI Loopback"


@dataclass(frozen=True, slots=True)
class AudioBlock:
    source_id: str
    samples: NDArray[np.float32]  # [frames, channels], somente leitura
    sample_rate: int
    channels: int
    sequence: int
    frames: int
    acquired_at: float  # início estimado do bloco, relógio monotônico
    received_at: float
    discontinuity: bool = False
    status_flags: int = 0


@dataclass(frozen=True, slots=True)
class CaptureFormat:
    sample_rate: int
    channels: int
    block_size: int
    sample_format: str = "float32"
    input_latency: float = 0.0


@dataclass(frozen=True, slots=True)
class TransientEvent:
    occurred_at: float
    detected_at: float
    intensity: float
    confidence: float  # indicador heurístico, não probabilidade calibrada


@dataclass(frozen=True, slots=True)
class SpectralSnapshot:
    frame_id: int
    frequencies_hz: tuple[float, ...]
    levels_db: tuple[float, ...]  # RMS por faixa logarítmica, dBFS
    band_ranges_hz: tuple[tuple[float, float], ...]
    band_levels_db: tuple[float, ...]
    band_fraction: tuple[float, ...]
    dominant_hz: float
    total_rms_db: float
    spectral_flux: float
    transient_score: float
    transient_threshold: float
    transient_count: int
    last_transient: TransientEvent | None
    sample_rate: int
    fft_size: int
    hop_size: int
    window_started_at: float
    window_ended_at: float
    dc_removed: bool
    filter_mode: str


@dataclass(frozen=True, slots=True)
class KickEvent:
    occurred_at: float  # centro estimado da janela, relógio de aquisição
    detected_at: float
    intensity: float  # força relativa ao histórico recente, 0–1
    confidence: float  # heurística; não é probabilidade calibrada


@dataclass(frozen=True, slots=True)
class KickSnapshot:
    frame_id: int
    analyzed_at: float
    band_db: float
    attack: float
    flux: float
    contrast: float
    low_fraction: float
    score: float
    threshold: float
    regularity: float
    count: int
    ready: bool
    last_event: KickEvent | None
    events: tuple[KickEvent, ...]  # últimos 16 eventos
    history: tuple[tuple[float, float, float], ...]  # tempo, atividade, limiar; 2 s
    band_hz: tuple[float, float]
    window_ms: float
    hop_ms: float


@dataclass(frozen=True, slots=True)
class TempoHypothesis:
    relation: str  # half, normal, double; não determina a métrica musical
    bpm: float
    score: float
    in_range: bool


@dataclass(frozen=True, slots=True)
class BeatSnapshot:
    updated_at: float
    state: str  # unlocked, acquiring, locked, coasting
    bpm: float
    period: float
    phase: float  # 0–1, zero na batida estimada
    beat_index: int  # contagem relativa, sem afirmar início de compasso
    last_beat_at: float | None
    next_beat_at: float | None
    last_reference_at: float | None
    expires_at: float | None
    confidence: float
    reference_confidence: float
    phase_error_ms: float
    matched_kicks: int
    rejected_kicks: int
    hypotheses: tuple[TempoHypothesis, ...]
    ambiguous: bool
    history: tuple[tuple[float, float, float], ...]  # tempo, BPM, confiança; até 120 pontos


@dataclass(frozen=True, slots=True)
class StructureFeatures:
    frame_id: int
    at: float
    low_db: float  # 30–180 Hz, sinal original independente do filtro de inspeção
    high_db: float  # 2–16 kHz
    rms_db: float
    brightness: float  # centroide normalizado, 0–1
    onset: bool  # ataque em 300 Hz–16 kHz, não classifica instrumento
    percussion_onset: bool = False  # ataque em 300–3000 Hz, evidência de roll
    percussion_db: float = -120.0
    low_shape: tuple[float, ...] = ()  # assinatura grave para confirmação estrutural
    harmonic_db: float = -120.0  # ataque harmônico em 250–1500 Hz
    bass_db: float = -120.0  # energia em 30–250 Hz
    texture_bands_db: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class KickGridSnapshot:
    updated_at: float
    state: str  # learning, tracking, predicting, expired
    period: float = 0.0
    anchor_at: float | None = None
    confidence: float = 0.0
    uncertainty_ms: float = 0.0
    next_kick_at: float | None = None  # janela esperada, não evento confirmado
    next_phrase_at: float | None = None  # frase relativa de oito tempos
    last_reference_at: float | None = None
    horizon_seconds: float = 0.0
    predictions: tuple[float, ...] = ()
    rejected_offgrid: int = 0
    forecast_30_at: float | None = None
    beat_index: int = 0
    phase: float = 0.0
    phrase_origin: int = 0
    revision: int = 0
    corrections: int = 0
    last_correction_ms: float = 0.0
    observations: int = 0
    jitter_ms: float = 4.0
    period_error_ms: float = 0.0
    reference_confidence: float = 0.9


@dataclass(frozen=True, slots=True)
class DropEvidenceSnapshot:
    reference_db: float | None = None
    candidate_db: float | None = None
    power_ratio: float = 0.0
    absent_beats: float = 0.0
    armed: bool = False
    pause_recent: bool = False
    accelerated: bool = False
    high_return: bool = False
    rejected_weak: int = 0
    reason: str = ""


@dataclass(frozen=True, slots=True)
class StructureSnapshot:
    updated_at: float
    state: str  # warming, groove, breakdown, buildup, drop, silence
    tension: float
    confidence: float
    energy: float
    brightness: float
    onset_rate: float
    kick_gap: float
    phrase_kick: int  # legado: agora tempo 1–8 da grade, não contagem de kicks
    bar_beat: int  # 1–4, hipótese 4/4, sem detecção automática de downbeat
    phrase_bar: int  # 1–2
    drop_kicks: int
    drop_id: int
    drop_at: float | None
    last_kick_at: float | None
    period: float  # último período confiável, não prolonga o PLL
    reason: str
    events: tuple["MusicalEvent", ...]
    roll_rate: float = 0.0
    roll_strength: float = 0.0
    grid: KickGridSnapshot | None = None
    rejected_timbre: int = 0
    kick_similarity: float = 0.0
    confirmed_kicks: tuple[KickEvent, ...] = ()
    acoustic_kicks: tuple[KickEvent, ...] = ()
    rejected_returns: int = 0
    reference_ready: bool = False
    timing_source: str = "audio"
    drop_evidence: DropEvidenceSnapshot | None = None


@dataclass(frozen=True, slots=True)
class TextureSnapshot:
    updated_at: float
    bass_db: float
    bass_level: float  # envelope de graves, não separação de instrumento
    bass_activity: float
    density: float  # ocupação/atividade; não número de instrumentos
    occupancy: float
    onset_rate: float
    brightness: float
    silent: bool = False


@dataclass(frozen=True, slots=True)
class KickVerificationSnapshot:
    updated_at: float
    confirmed_count: int
    acoustic_count: int
    expected_count: int
    matched_count: int
    missed_count: int
    confirmed_events: tuple[KickEvent, ...]
    acoustic_events: tuple[KickEvent, ...]
    slots: tuple[tuple[float, str], ...]  # confirmado, grave rejeitado, sem kick
    grid: KickGridSnapshot | None = None
    rejected_profile: int = 0
    rejected_grid: int = 0
    last_confirmed_at: float | None = None


@dataclass(frozen=True, slots=True)
class MonitorSnapshot:
    sequence: int
    waveform: tuple[tuple[float, ...], ...]
    rms_db: tuple[float, ...]
    peak_db: tuple[float, ...]
    silent: bool
    clipping: bool
    acquired_at: float
    processed_at: float
    processing_ms: float
    delivery_ms: float
    continuity_errors: int
    spectral: SpectralSnapshot | None = None
    analysis_error: str = ""
    kicks: KickSnapshot | None = None
    kick_error: str = ""
    beat: BeatSnapshot | None = None
    beat_error: str = ""
    structure: StructureSnapshot | None = None
    structure_error: str = ""
    texture: TextureSnapshot | None = None
    texture_error: str = ""
    kick_verification: KickVerificationSnapshot | None = None
    kick_verification_error: str = ""
    timing_source: str = "audio"


@dataclass(frozen=True, slots=True)
class RuntimeStatus:
    state: str
    message: str
    blocks: int
    dropped_blocks: int
    queue_depth: int
    elapsed: float
    audio_age: float
    stream_format: CaptureFormat | None
    error: str = ""
    notice: str = ""


class AudioSource(Protocol):
    """start/stop pertencem à thread de controle; callback não deve bloquear.

    start retorna o formato realmente aberto. stop só retorna quando a fonte
    não produzir mais blocos; stop é idempotente. poll_error relata falhas
    assíncronas e pode ser chamado pela thread de análise.
    """
    def devices(self) -> list[AudioDevice]: ...
    def start(self, device: AudioDevice, block_size: int,
              on_block: Callable[[AudioBlock], None]) -> CaptureFormat: ...
    def stop(self) -> None: ...
    def poll_error(self) -> str | None: ...
    def poll_notice(self) -> str | None: ...


class BlockAnalyzer(Protocol):
    def process(self, block: AudioBlock) -> MonitorSnapshot: ...


# Eventos de estrutura musical; saídas físicas continuam atrás de adaptadores.
@dataclass(frozen=True, slots=True)
class MusicalEvent:
    kind: str
    occurred_at: float
    confidence: float
    intensity: float


@dataclass(frozen=True, slots=True)
class FixtureState:
    fixture_id: str
    intensity: float
    color: tuple[float, float, float]
    pan: float = 0.0
    tilt: float = 0.0
    white: float = 0.0  # canal W independente; color contém os canais R/G/B

    def __post_init__(self):
        values = (self.intensity, *self.color, self.pan, self.tilt, self.white)
        if (not self.fixture_id or len(self.color) != 3 or
                any(type(v) not in (float, int) or not math.isfinite(v) or not 0 <= v <= 1 for v in values)):
            raise ValueError("Estado de luminária inválido: parâmetros normalizados devem estar entre 0 e 1.")


@dataclass(frozen=True, slots=True)
class FixtureDefinition:
    fixture_id: str
    name: str
    kind: str  # par ou moving_head abstratos, sem personalidade DMX
    groups: tuple[str, ...]
    capabilities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LightingInput:
    source_active: bool = False
    audio_fresh: bool = False
    kicks: tuple[KickEvent, ...] = ()
    beat: BeatSnapshot | None = None
    structure: StructureSnapshot | None = None
    texture: TextureSnapshot | None = None
    confirmed_kicks: tuple[KickEvent, ...] | None = None
    kick_confirmed_at: float | None = None


@dataclass(frozen=True, slots=True)
class LightingSnapshot:
    frame_id: int
    updated_at: float
    states: tuple[FixtureState, ...]
    effect: str
    status: str
    reason: str
    master: float
    blackout: bool
    manual: bool
    beat_state: str
    processing_ms: float = 0.0
    update_hz: float = 0.0
    error: str = ""
    movement_hz: float = 0.0
    white_mix: float = 0.0
    color_profile: str = "fixed"
    show_pattern: str = ""
    show_step: int = 0
    show_fills: int = 0
    show_novelty: float = 0.0
    phrase_step: int = 0
    phrase_cycle: int = 0
    phrase_phase: float = 0.0
    phrase_gain: float = 1.0
    phrase_preparation: bool = False
    phrase_pending: bool = False
    phrase_synced: bool = False
    phrase_sync_id: int = 0
    phrase_pattern: str = ""
    phrase_repetition: int = 0
    phrase_sync_flash: bool = False
    phrase_change_reason: str = ""
    show_rhythm: str = ""
    show_masks: tuple[int, ...] = ()
    show_phase: float = 0.0
    mover_rhythm: str = ""
    breakdown_calm: bool = False
    breakdown_blend: float = 0.0


class LightingOutput(Protocol):
    def send(self, states: tuple[FixtureState, ...]) -> None: ...
    def blackout(self) -> None: ...
    def close(self) -> None: ...
