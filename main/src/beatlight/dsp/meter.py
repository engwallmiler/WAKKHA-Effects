"""Medição inicial de áudio; independente de interface e fonte de captura."""
from collections import deque
from time import monotonic, perf_counter
import numpy as np
from beatlight.contracts import AudioBlock, MonitorSnapshot


def amplitude_db(value: np.ndarray) -> tuple[float, ...]:
    return tuple(float(v) for v in 20 * np.log10(np.maximum(value, 1e-6)))


class LevelAnalyzer:
    def __init__(self, silence_db: float = -65.0):
        self.silence_db = silence_db
        self._last_sequence: int | None = None
        self._continuity_errors = 0
        self._history: deque[np.ndarray] = deque()
        self._frames = 0
        self._signature: tuple[int, int] | None = None

    def process(self, block: AudioBlock) -> MonitorSnapshot:
        started = perf_counter()
        x = block.samples
        if x.shape != (block.frames, block.channels) or not np.isfinite(x).all():
            raise ValueError("Bloco de áudio inválido ou com amostras não finitas.")
        if block.discontinuity or (self._last_sequence is not None
                                  and block.sequence != self._last_sequence + 1):
            self._continuity_errors += 1
        self._last_sequence = block.sequence
        signature = (block.sample_rate, block.channels)
        if signature != self._signature:
            self._history.clear()
            self._frames = 0
            self._signature = signature
        # Sem normalização: preserva dinâmica, clipping e silêncio do sinal original.
        rms = np.sqrt(np.mean(np.square(x, dtype=np.float64), axis=0))
        peak = np.max(np.abs(x), axis=0)
        rms_db, peak_db = amplitude_db(rms), amplitude_db(peak)
        self._history.append(x)
        self._frames += block.frames
        # Janela visual de 200 ms, separada da entrega dos blocos para análise.
        limit = max(block.frames, int(block.sample_rate * 0.2))
        while len(self._history) > 1 and self._frames - len(self._history[0]) >= limit:
            self._frames -= len(self._history.popleft())
        history = np.concatenate(tuple(self._history), axis=0)[-limit:]
        # Envelope min/max por coluna: preserva transientes sem enviar cada amostra à UI.
        columns = min(480, len(history))
        edges = np.linspace(0, len(history), columns + 1, dtype=int)
        # Duas reduções vetoriais substituem até 1.920 chamadas NumPy por bloco.
        # Os intervalos e extremos são idênticos aos do envelope anterior.
        lower = np.minimum.reduceat(history, edges[:-1], axis=0)
        upper = np.maximum.reduceat(history, edges[:-1], axis=0)
        envelope = np.stack((lower, upper), axis=-1).transpose(1, 0, 2)
        waveform = tuple(tuple(row) for row in envelope.reshape(block.channels, -1).tolist())
        processed_at = monotonic()
        return MonitorSnapshot(
            sequence=block.sequence, waveform=tuple(waveform), rms_db=rms_db,
            peak_db=peak_db, silent=max(rms_db) < self.silence_db,
            clipping=bool(np.any(peak >= 0.999)), acquired_at=block.acquired_at,
            processed_at=processed_at, processing_ms=(perf_counter() - started) * 1000,
            delivery_ms=max(0.0, (processed_at - block.received_at) * 1000),
            continuity_errors=self._continuity_errors,
        )
