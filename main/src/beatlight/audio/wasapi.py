"""Adaptador WASAPI Loopback. PortAudio fica totalmente contido neste arquivo."""
import importlib
import logging
import sys
from threading import Event, Lock, Thread
from time import monotonic
from typing import Callable
import numpy as np
from beatlight.contracts import AudioBlock, AudioDevice, CaptureFormat

log = logging.getLogger(__name__)


class WasapiSource:
    def __init__(self, module=None, health_interval: float = 3.0):
        self._module = module
        self._health_interval = health_interval
        self._pa = None
        self._stream = None
        self._error: str | None = None
        self._lock = Lock()
        self._running = False
        self._health_stop = Event()
        self._health_thread: Thread | None = None
        self._notice: str | None = None

    def _library(self):
        if self._module is None:
            if sys.platform != "win32":
                raise RuntimeError("WASAPI Loopback está disponível somente no Windows.")
            try:
                self._module = importlib.import_module("pyaudiowpatch")
            except ImportError as exc:
                raise RuntimeError("Instale PyAudioWPatch para usar a captura WASAPI.") from exc
        return self._module

    @staticmethod
    def _enumerate(pa) -> list[tuple[AudioDevice, dict]]:
        try:
            default = pa.get_default_wasapi_loopback()
            default_index = default["index"]
        except (OSError, ValueError):
            default_index = -1
        occurrences: dict[str, int] = {}
        result = []
        for info in pa.get_loopback_device_info_generator():
            channels = int(info["maxInputChannels"])
            if channels < 1:
                continue
            name = str(info["name"])
            occurrence = occurrences.get(name, 0)
            occurrences[name] = occurrence + 1
            device = AudioDevice(
                id=f"wasapi:{name}:{occurrence}",
                name=name.replace("[Loopback]", "").strip(),
                sample_rate=int(info["defaultSampleRate"]), channels=channels,
                is_default=info["index"] == default_index,
            )
            result.append((device, info))
        return result

    def devices(self) -> list[AudioDevice]:
        lib = self._library()
        pa = lib.PyAudio()
        try:
            return [device for device, _ in self._enumerate(pa)]
        finally:
            pa.terminate()

    def start(self, device: AudioDevice, block_size: int,
              on_block: Callable[[AudioBlock], None]) -> CaptureFormat:
        if self._pa is not None:
            raise RuntimeError("A captura já está aberta.")
        lib = self._library()
        self._error = None
        self._notice = None
        self._pa = lib.PyAudio()
        try:
            # Índices PortAudio mudam após reconexões: resolver novamente pela identidade.
            available = self._enumerate(self._pa)
            match = next(((d, info) for d, info in available
                          if d.id == device.id), None)
            if match is None:
                raise RuntimeError("A saída selecionada foi desconectada. Atualize os dispositivos.")
            actual, info = match
            rate, channels = actual.sample_rate, actual.channels
            sequence = 0
            last_acquired: float | None = None
            clock_offset: float | None = None

            def callback(data, frames, timing, flags):
                nonlocal sequence, last_acquired, clock_offset
                received = monotonic()
                try:
                    samples = np.frombuffer(data, dtype=np.float32).reshape(frames, channels)
                    samples.setflags(write=False)
                    # Mapeia o relógio PortAudio para a referência monotônica comum.
                    current = float(timing.get("current_time", 0.0))
                    adc = float(timing.get("input_buffer_adc_time", 0.0))
                    if current > 0 and adc > 0:
                        if clock_offset is None:
                            clock_offset = received - current
                        acquired = adc + clock_offset
                        if acquired > received or received - acquired > 2.0:
                            acquired = received - frames / rate
                    else:
                        acquired = received - frames / rate
                    discontinuity = bool(flags) or (
                        last_acquired is not None
                        and abs(acquired - last_acquired - frames / rate) > max(0.05, frames / rate * 2)
                    )
                    last_acquired = acquired
                    on_block(AudioBlock(actual.id, samples, rate, channels, sequence,
                                        frames, acquired, received, discontinuity, int(flags)))
                    sequence += 1
                    return None, lib.paContinue
                except Exception as exc:
                    with self._lock:
                        self._error = f"Falha no callback de áudio: {exc}"
                    return None, lib.paAbort

            self._stream = self._pa.open(
                format=lib.paFloat32, channels=channels, rate=rate, input=True,
                input_device_index=int(info["index"]), frames_per_buffer=block_size,
                stream_callback=callback, start=False,
            )
            latency = float(self._stream.get_input_latency())
            self._stream.start_stream()
            self._running = True
            self._watch_device(actual, next((d.id for d, _ in available if d.is_default), ""))
            log.info("capture_started", extra={"device": actual.name, "rate": rate,
                                               "channels": channels, "block_size": block_size})
            return CaptureFormat(rate, channels, block_size, input_latency=latency)
        except Exception:
            self.stop()
            raise

    def poll_error(self) -> str | None:
        with self._lock:
            if self._error:
                return self._error
        if self._running and self._stream is not None:
            try:
                if not self._stream.is_active():
                    return "O dispositivo interrompeu a captura. Atualize a lista e reinicie."
            except OSError as exc:
                return f"Dispositivo indisponível: {exc}"
            # WASAPI pode deixar de entregar blocos quando não há reprodução.
            # Inatividade não comprova desconexão; a descoberta periódica verifica isso.
        return None

    def _watch_device(self, selected: AudioDevice, initial_default: str) -> None:
        stop = Event()
        self._health_stop = stop
        def check():
            default_id = initial_default
            while not stop.wait(self._health_interval):
                try:
                    devices = self.devices()
                    if stop.is_set():
                        return
                    current_default = next((d.id for d in devices if d.is_default), "")
                    if not any(d.id == selected.id for d in devices):
                        with self._lock:
                            self._error = "A saída selecionada foi removida. Atualize os dispositivos e reinicie."
                        return
                    if default_id is not None and current_default != default_id:
                        with self._lock:
                            self._notice = ("A saída padrão do Windows mudou. A captura permanece em "
                                            + selected.name + ". Pare e selecione outra saída se necessário.")
                        log.warning("default_output_changed")
                    default_id = current_default
                except Exception as exc:
                    log.warning("device_health_check_failed", extra={"reason": str(exc)})
        self._health_thread = Thread(target=check, name="wasapi-device-health", daemon=True)
        self._health_thread.start()

    def poll_notice(self) -> str | None:
        with self._lock:
            notice, self._notice = self._notice, None
            return notice

    def stop(self) -> None:
        self._running = False
        self._health_stop.set()
        if self._health_thread is not None:
            self._health_thread.join(timeout=2)
            self._health_thread = None
        stream, pa = self._stream, self._pa
        self._stream, self._pa = None, None
        try:
            if stream is not None:
                try:
                    stream.stop_stream()
                finally:
                    stream.close()
        finally:
            if pa is not None:
                pa.terminate()
        log.info("capture_stopped")
