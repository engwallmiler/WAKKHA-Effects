"""Ciclo de vida e snapshots; sem dependência de Qt ou PortAudio."""
import logging
from threading import Event, Lock, RLock, Thread
from time import monotonic
from typing import Callable
from beatlight.contracts import AudioDevice, AudioSource, BlockAnalyzer, CaptureFormat, MonitorSnapshot, RuntimeStatus
from beatlight.dsp.pipeline import AudioAnalyzer
from beatlight.streams.buffer import RecentBlockQueue

log = logging.getLogger(__name__)


class CaptureRuntime:
    def __init__(self, queue_capacity: int = 8, silence_db: float = -65.0,
                 analyzer_factory: Callable[[], BlockAnalyzer] | None = None):
        self.queue = RecentBlockQueue(queue_capacity)
        self.silence_db = silence_db
        self._analyzer_factory = analyzer_factory or (lambda: AudioAnalyzer(self.silence_db))
        self._lock = Lock()
        self._control = RLock()
        self._stop = Event()
        self._ready = Event()
        self._thread: Thread | None = None
        self._snapshot: MonitorSnapshot | None = None
        self._state = "stopped"
        self._message = "Pronto para monitorar"
        self._error = ""
        self._notice = ""
        self._format: CaptureFormat | None = None
        self._blocks = 0
        self._started_at = 0.0
        self._ended_at = 0.0
        self._last_received = 0.0

    def start(self, source: AudioSource, device: AudioDevice, block_size: int) -> None:
        if block_size not in (256, 512, 1024, 2048):
            raise ValueError("Tamanho de bloco inválido.")
        with self._control:
            self.stop()
            self.queue.reset()
            self._stop.clear()
            self._ready.clear()
            with self._lock:
                self._state, self._message, self._error = "starting", "Abrindo dispositivo…", ""
                self._snapshot, self._format = None, None
                self._notice = ""
                self._blocks = 0
                self._started_at = monotonic()
                self._last_received = self._started_at
                self._ended_at = 0.0
            self._thread = Thread(target=self._run, args=(source, device, block_size),
                                  name="audio-analysis", daemon=True)
            self._thread.start()
            if not self._ready.wait(8):
                self._stop.set()
                raise RuntimeError("O dispositivo demorou demais para abrir. Aguarde o encerramento.")
            with self._lock:
                error = self._error
            if error:
                raise RuntimeError(error)

    def _receive(self, block) -> None:
        self.queue.put(block)
        with self._lock:
            self._blocks += 1
            self._last_received = block.received_at

    def _run(self, source: AudioSource, device: AudioDevice, block_size: int) -> None:
        try:
            analyzer = self._analyzer_factory()
            actual_format = source.start(device, block_size, self._receive)
            with self._lock:
                self._format = actual_format
                self._state, self._message = "running", "Aguardando sinal de áudio"
            self._ready.set()
            while not self._stop.is_set():
                error = source.poll_error()
                if error:
                    raise RuntimeError(error)
                notice = source.poll_notice()
                if notice:
                    with self._lock:
                        self._notice = notice
                block = self.queue.get(0.1)
                if block is None:
                    continue
                snapshot = analyzer.process(block)
                with self._lock:
                    self._snapshot = snapshot
                    self._message = "Sem sinal • silêncio detectado" if snapshot.silent else "Monitorando áudio"
        except Exception as exc:
            log.exception("capture_failed")
            with self._lock:
                self._error = str(exc)
                self._state, self._message = "error", "Captura interrompida"
        finally:
            try:
                source.stop()
            except Exception as exc:
                log.exception("capture_cleanup_failed")
                with self._lock:
                    self._error = self._error or f"Falha ao fechar o dispositivo: {exc}"
            with self._lock:
                self._ended_at = monotonic()
                if self._error:
                    self._state = "error"
                    self._message = "Captura interrompida"
                else:
                    self._state, self._message = "stopped", "Captura encerrada"
            self._ready.set()

    def stop(self) -> None:
        with self._control:
            self._stop.set()
            if self._thread and self._thread.is_alive():
                with self._lock:
                    self._state, self._message = "stopping", "Encerrando captura…"
                self._thread.join(timeout=6)
                if self._thread.is_alive():
                    raise RuntimeError("O driver ainda não encerrou. Não será aberta outra captura.")
            self._thread = None

    def snapshot(self) -> MonitorSnapshot | None:
        with self._lock:
            return self._snapshot

    def status(self) -> RuntimeStatus:
        dropped, depth = self.queue.metrics()
        now = monotonic()
        with self._lock:
            end = self._ended_at or now
            elapsed = max(0, end - self._started_at) if self._started_at else 0
            return RuntimeStatus(self._state, self._message, self._blocks, dropped, depth,
                                 elapsed, max(0, now - self._last_received),
                                 self._format, self._error, self._notice)
