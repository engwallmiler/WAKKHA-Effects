"""Compõe medidores, kicks, Beat Tracker e análise espectral opcional."""
from dataclasses import replace
import logging
from time import monotonic, perf_counter
from beatlight.contracts import AudioBlock, MonitorSnapshot, SpectralSnapshot
from beatlight.dsp.config import DspConfig
from beatlight.dsp.kick_config import KickConfig
from beatlight.dsp.kicks import KickDetector
from beatlight.dsp.meter import LevelAnalyzer
from beatlight.music.config import BeatConfig
from beatlight.music.tracker import BeatTracker
from beatlight.dsp.preprocess import AudioPreprocessor
from beatlight.dsp.spectrum import StreamingSpectrum
from beatlight.dsp.transients import TransientDetector
from beatlight.dsp.structure_features import StructureFeatureExtractor
from beatlight.music.structure import StructureTracker
from beatlight.music.texture import TextureTracker
from beatlight.music.kick_audit import KickAudit

log = logging.getLogger(__name__)


class AudioAnalyzer:
    def __init__(self, silence_db: float = -65.0, config: DspConfig | None = None,
                 kick_config: KickConfig | None = None,
                 beat_config: BeatConfig | None = None, clock_provider=None):
        self._clock_provider = clock_provider
        self.config = config or DspConfig()
        self._texture = TextureTracker()
        self._texture_latest = None
        self._texture_error = ""
        self._audit = KickAudit()
        self._audit_latest = None
        self._audit_error = ""
        self._feature_failed_signature = None
        self._texture_failed_signature = None
        self._audit_failed_signature = None
        self._structure = StructureTracker(beat_config)
        self._structure_features = StructureFeatureExtractor()
        self._structure_latest = None
        self._structure_error = ""
        self._structure_signature = None
        self._structure_failed_signature = None
        self._beats = BeatTracker(beat_config)
        self._beat_latest = None
        self._beat_error = ""
        self._beat_failed_signature = None
        self._beat_signature = None
        self._beat_at = 0.0
        self._kicks = KickDetector(kick_config)
        self._kick_latest = None
        self._kick_error = ""
        self._kick_failed_signature = None
        self._levels = LevelAnalyzer(silence_db)
        self._spectrum = StreamingSpectrum(self.config)
        self._transients = TransientDetector()
        self._preprocessor = None
        self._signature = None
        self._last_sequence = None
        self._last_audio_end = None
        self._last_block_signature = None
        self._latest = None
        self._analysis_error = ""
        self._failed_signature = None

    def process(self, block: AudioBlock) -> MonitorSnapshot:
        started = perf_counter()
        received_for_processing = monotonic()
        signature = block.source_id, block.sample_rate, block.channels
        if (signature == self._last_block_signature and self._last_audio_end is not None
                and block.acquired_at - self._last_audio_end > 0.5):
            # WASAPI pode parar callbacks no silêncio sem mudar a sequência.
            block = replace(block, discontinuity=True)
        self._last_audio_end = block.acquired_at + block.frames / block.sample_rate
        self._last_block_signature = signature
        levels = self._levels.process(block)
        gap = (block.discontinuity or (self._last_sequence is not None
                                      and block.sequence != self._last_sequence + 1))
        self._last_sequence = block.sequence
        if signature != self._kick_failed_signature:
            try:
                self._kick_latest = self._kicks.push(block)
                self._kick_error = ""
                self._kick_failed_signature = None
            except Exception as exc:
                log.exception("kick_analysis_failed")
                self._kick_latest = None
                self._kick_error = str(exc)
                self._kick_failed_signature = signature
        if signature != self._beat_failed_signature:
            try:
                if signature != self._beat_signature or gap or block.status_flags:
                    self._beats.reset()
                    self._beat_at = 0.0
                    self._beat_signature = signature
                self._beat_at = max(self._beat_at, block.acquired_at + block.frames / block.sample_rate)
                events = self._kick_latest.events if self._kick_latest else ()
                self._beat_latest = self._beats.process(events, self._beat_at)
                self._beat_error = ""
                self._beat_failed_signature = None
            except Exception as exc:
                log.exception("beat_tracking_failed")
                self._beat_latest = None
                self._beat_error = str(exc)
                self._beat_failed_signature = signature
        if signature != self._failed_signature:
            try:
                if signature != self._signature or gap:
                    self._preprocessor = AudioPreprocessor(self.config, block.sample_rate, block.channels)
                    self._spectrum.reset()
                    self._transients.reset()
                    self._latest = None
                    self._signature = signature
                samples = self._preprocessor.process(block.samples)
                for frame in self._spectrum.push(samples, block.sample_rate, block.acquired_at):
                    self._transients.process(frame)
                    self._latest = SpectralSnapshot(
                        frame.id, frame.display_frequencies, frame.display_db,
                        self.config.bands, frame.band_levels_db, frame.band_fraction,
                        frame.dominant_hz, frame.rms_db, self._transients.flux,
                        self._transients.score, self._transients.threshold, self._transients.count,
                        self._transients.last_event, block.sample_rate, self.config.fft_size,
                        self.config.hop_size, frame.started_at, frame.ended_at,
                        self.config.remove_dc, self.config.filter_mode,
                    )
                self._analysis_error = ""
                self._failed_signature = None
            except Exception as exc:
                # Uma falha opcional do espectro não interrompe os medidores/captura.
                log.exception("spectral_analysis_failed")
                self._latest = None
                self._analysis_error = str(exc)
                self._failed_signature = signature
        self._process_music_features(block, signature, gap)
        ended = monotonic()
        return replace(levels, spectral=self._latest, analysis_error=self._analysis_error,
                       kicks=self._kick_latest, kick_error=self._kick_error,
                       beat=self._beat_latest, beat_error=self._beat_error,
                       structure=self._structure_latest, structure_error=self._structure_error,
                       texture=self._texture_latest, texture_error=self._texture_error,
                       kick_verification=self._audit_latest, kick_verification_error=self._audit_error,
                       processed_at=ended, processing_ms=(perf_counter() - started) * 1000,
                       delivery_ms=max(0.0, (received_for_processing - block.received_at) * 1000))

    def _process_music_features(self, block, signature, gap):
        if signature != self._structure_signature or gap or block.status_flags:
            self._structure.reset()
            self._structure_features.reset()
            self._texture = TextureTracker()
            self._audit = KickAudit()
            self._structure_latest = self._texture_latest = self._audit_latest = None
            self._structure_error = self._texture_error = self._audit_error = ""
            self._feature_failed_signature = self._texture_failed_signature = None
            self._structure_failed_signature = self._audit_failed_signature = None
            self._structure_signature = signature
        if signature == self._feature_failed_signature:
            return
        try:
            features = self._structure_features.push(block)
        except Exception as exc:
            log.exception("structure_features_failed")
            self._feature_failed_signature = signature
            self._structure_error = self._texture_error = self._audit_error = str(exc)
            self._structure_latest = self._texture_latest = self._audit_latest = None
            return
        events = self._kick_latest.events if self._kick_latest and not self._kick_error else ()
        for feature in features:
            if signature != self._texture_failed_signature:
                try:
                    self._texture_latest = self._texture.process(feature)
                except Exception as exc:
                    log.exception("texture_analysis_failed")
                    self._texture_error, self._texture_latest = str(exc), None
                    self._texture_failed_signature = signature
            if signature != self._structure_failed_signature:
                try:
                    external = None
                    if self._clock_provider:
                        try:
                            external = self._clock_provider(feature.at)
                        except Exception:
                            log.warning("external_clock_unavailable", exc_info=True)
                    self._structure_latest = self._structure.process(feature, events,
                        external or (self._beat_latest if not self._beat_error else None))
                except Exception as exc:
                    log.exception("structure_analysis_failed")
                    self._structure_error, self._structure_latest = str(exc), None
                    self._structure_failed_signature = signature
            if self._structure_error:
                self._audit_latest = None
                self._audit_error = "Estrutura indisponível; kicks não confirmados."
            elif self._structure_latest and signature != self._audit_failed_signature:
                try:
                    self._audit_latest = self._audit.process(self._structure_latest, events)
                    self._audit_error = ""
                except Exception as exc:
                    log.exception("kick_verification_failed")
                    self._audit_error, self._audit_latest = str(exc), None
                    self._audit_failed_signature = signature
