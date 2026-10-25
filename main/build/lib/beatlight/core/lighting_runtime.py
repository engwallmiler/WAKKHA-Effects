"""Worker de iluminação independente do DSP e da GUI; sem saída física."""
from dataclasses import replace
import logging
from threading import Event, Lock, Thread
from time import monotonic, perf_counter
from typing import Callable
from beatlight.contracts import LightingInput, LightingSnapshot
from beatlight.lighting.config import LightingControls
from beatlight.lighting.engine import LightingEngine

log = logging.getLogger(__name__)


class LightingRuntime:
    def __init__(self, provider: Callable, controls: LightingControls | None = None,
                 rate_hz: int = 60, engine: LightingEngine | None = None):
        if type(rate_hz) is not int or not 10 <= rate_hz <= 120:
            raise ValueError("Frequência do motor deve estar entre 10 e 120 Hz.")
        self.engine = engine or LightingEngine()
        self.rate_hz = rate_hz
        self._provider = provider
        self._controls = controls or LightingControls()
        self._lock = Lock()
        self._stop = Event()
        self._thread = None
        self._revision = 0
        self._snapshot = self.engine.render(LightingInput(), self._controls, monotonic())

    def controls(self) -> LightingControls:
        with self._lock:
            return self._controls

    def set_controls(self, controls: LightingControls):
        if not isinstance(controls, LightingControls):
            raise ValueError("Comando de iluminação inválido.")
        with self._lock:
            if self._controls != controls:
                self._controls = controls
                self._revision += 1

    def snapshot(self) -> LightingSnapshot:
        with self._lock:
            return self._snapshot

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(target=self._run, name="lighting-engine", daemon=True)
        self._thread.start()

    def _publish_dark(self, status, reason, error=""):
        with self._lock:
            previous, controls = self._snapshot, self._controls
            self._snapshot = replace(previous, updated_at=monotonic(),
                states=tuple(replace(s, intensity=0.0, color=(0.0, 0.0, 0.0), white=0.0) for s in previous.states),
                status=status, reason=reason, blackout=controls.blackout,
                manual=controls.manual, master=controls.config.light_master, error=error, movement_hz=0.0, white_mix=0.0,
                show_pattern="", show_step=0, show_rhythm="", show_masks=(), show_phase=0.0,
                phrase_step=0, phrase_cycle=0, phrase_phase=0.0, phrase_gain=1.0,
                phrase_pending=False, phrase_preparation=False, phrase_synced=False, phrase_sync_flash=False,
                phrase_change_reason="", phrase_pattern="", phrase_repetition=0,
                mover_rhythm="", breakdown_calm=False, breakdown_blend=0.0)

    def _run(self):
        interval = 1 / self.rate_hz
        count, measured_hz, window_start = 0, 0.0, monotonic()
        failed_revision = None
        deadline = perf_counter()
        while not self._stop.is_set():
            started = perf_counter()
            at = monotonic()
            with self._lock:
                controls, revision = self._controls, self._revision
            if failed_revision != revision:
                try:
                    snapshot, status = self._provider()
                    music = LightingInput(status.state == "running", status.audio_age < 0.5,
                        snapshot.kicks.events if snapshot and snapshot.kicks and not snapshot.kick_error else (),
                        snapshot.beat if snapshot and not snapshot.beat_error else None,
                        snapshot.structure if snapshot and not snapshot.structure_error and not snapshot.kick_error else None,
                        texture=snapshot.texture if snapshot and not snapshot.texture_error else None,
                        confirmed_kicks=(snapshot.kick_verification.confirmed_events if snapshot and snapshot.kick_verification
                            and not snapshot.kick_verification_error and not snapshot.structure_error else ()),
                        kick_confirmed_at=(snapshot.kick_verification.last_confirmed_at if snapshot and snapshot.kick_verification
                            and not snapshot.kick_verification_error and not snapshot.structure_error else None))
                    result = self.engine.render(music, controls, at)
                    count += 1
                    if at - window_start >= 1:
                        measured_hz = count / (at - window_start)
                        count, window_start = 0, at
                    result = replace(result, processing_ms=(perf_counter() - started) * 1000,
                                     update_hz=measured_hz)
                    with self._lock:
                        self._snapshot = result
                except Exception as exc:
                    log.exception("lighting_engine_failed")
                    self._publish_dark("error", "Falha no motor; estados zerados. Altere um controle para tentar novamente.", str(exc))
                    failed_revision = revision
            # Prazo absoluto evita acumular a granularidade de espera do Windows.
            deadline += interval
            now_perf = perf_counter()
            if deadline < now_perf:
                deadline = now_perf
            self._stop.wait(max(0, deadline - now_perf))
        self._publish_dark("stopped", "Motor encerrado; intensidades zeradas.")

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
            if self._thread.is_alive():
                raise RuntimeError("O motor de iluminação ainda não encerrou.")
        self._thread = None
        self._publish_dark("stopped", "Motor encerrado; intensidades zeradas.")

    @property
    def running(self):
        return bool(self._thread and self._thread.is_alive())
