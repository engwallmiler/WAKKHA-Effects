"""Fonte sintética apenas para validação; não comprova desempenho com música real."""
from threading import Event, Thread
from time import monotonic
from typing import Callable
import numpy as np
from beatlight.contracts import AudioBlock, AudioDevice, CaptureFormat
from beatlight.audio.demo import structure_demo_samples
from beatlight.audio.texture_demo import texture_demo_samples


class SyntheticSource:
    DEVICE = AudioDevice("test:stereo", "Sinal sintético estéreo", 48000, 2, True,
                         "Teste sintético • sem captura do Windows")

    def __init__(self, silence: bool = False, structure_demo: bool = False, texture_demo: bool = False):
        if structure_demo and texture_demo:
            raise ValueError("Escolha somente uma composição de teste.")
        self.structure_demo = structure_demo
        self.texture_demo = texture_demo
        self.silence = silence
        self._stop = Event()
        self._thread: Thread | None = None
        self._error: str | None = None

    def devices(self) -> list[AudioDevice]:
        return [self.DEVICE]

    def start(self, device: AudioDevice, block_size: int,
              on_block: Callable[[AudioBlock], None]) -> CaptureFormat:
        if self._thread and self._thread.is_alive():
            raise RuntimeError("O teste já está em execução.")
        if device.id != self.DEVICE.id:
            raise ValueError("Fonte sintética desconhecida.")
        self._stop.clear()
        self._error = None

        def generate():
            start = monotonic()
            sequence = 0
            rate = self.DEVICE.sample_rate
            try:
                while not self._stop.is_set():
                    acquired = start + sequence * block_size / rate
                    # Emula aquisição: entrega quando o bloco inteiro foi gerado.
                    if self._stop.wait(max(0, acquired + block_size / rate - monotonic())):
                        break
                    t = (np.arange(block_size) + sequence * block_size) / rate
                    pulse = np.exp(-((t * 2.0) % 1.0) * 12.0)
                    left = 0.45 * pulse * np.sin(2 * np.pi * 70 * t) + 0.08 * np.sin(2 * np.pi * 440 * t)
                    right = 0.4 * pulse * np.sin(2 * np.pi * 85 * t) + 0.08 * np.sin(2 * np.pi * 660 * t)
                    # Camada aguda controlada para inspecionar as três bandas no monitor.
                    treble = np.exp(-((t * 4.0) % 1.0) * 15.0)
                    left += 0.035 * treble * np.sin(2 * np.pi * 6000 * t)
                    right += 0.035 * treble * np.sin(2 * np.pi * 9000 * t)
                    samples = np.column_stack((left, right)).astype(np.float32)
                    if self.structure_demo:
                        samples = structure_demo_samples(t)
                    if self.texture_demo:
                        samples = texture_demo_samples(t)
                    if self.silence:
                        samples.fill(0)
                    samples.setflags(write=False)
                    on_block(AudioBlock(device.id, samples, rate, 2, sequence, block_size,
                                        acquired, monotonic()))
                    sequence += 1
            except Exception as exc:
                self._error = str(exc)

        self._thread = Thread(target=generate, name="synthetic-input", daemon=True)
        self._thread.start()
        return CaptureFormat(self.DEVICE.sample_rate, 2, block_size)

    def poll_error(self) -> str | None:
        return self._error

    def poll_notice(self) -> str | None:
        return None

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
            if self._thread.is_alive():
                raise RuntimeError("A fonte sintética não encerrou no prazo esperado.")
        self._thread = None
