"""Leitor Ableton Link. Toda chamada nativa pertence a uma thread própria.

Não envia comandos de mudança de tempo, transporte ou reposicionamento.
A sessão usa o tempo inicial do primeiro participante; ative o Traktor primeiro.
Link sincroniza relógios;
não informa qual deck/track está tocando e nunca cria eventos de kick.
"""
import asyncio
from dataclasses import dataclass
from importlib.util import find_spec
from functools import lru_cache
import math
from threading import Event, Lock, RLock, Thread
from time import monotonic


@dataclass(frozen=True, slots=True)
class LinkSnapshot:
    updated_at: float = 0.0
    state: str = "disabled"  # disabled, starting, waiting, connected, error
    tempo: float = 0.0
    beat: float = 0.0
    peers: int = 0
    revision: int = 0
    sample_ms: float = 0.0
    error: str = ""

    def usable(self, at):
        return (self.state == "connected" and self.peers > 0
                and -.25 <= at - self.updated_at <= .5
                and math.isfinite(self.tempo) and 20 <= self.tempo <= 999
                and math.isfinite(self.beat))


class NativeLink:
    """API mínima: ativação local e leituras; sem setters de tempo/fase."""
    def __init__(self):
        from aalink import Link
        self._link = Link(120.0)  # chamado dentro do loop asyncio do worker
        self._link.quantum = 8.0  # só a interpretação local do ciclo visual
        self._link.enabled = True

    def read(self):
        before = monotonic()
        tempo = float(self._link.tempo)
        beat = float(self._link.beat)
        after = monotonic()
        if tempo != float(self._link.tempo):
            return None  # amostra atravessou uma mudança de tempo
        return (before + after) / 2, tempo, beat, int(self._link.num_peers), (after - before) * 1000

    def close(self):
        self._link.enabled = False
        self._link = None


class LinkRuntime:
    def __init__(self, backend_factory=NativeLink):
        self._factory = backend_factory
        self._lock, self._control = Lock(), RLock()
        self._stop = Event()
        self._thread = None
        self._snapshot = LinkSnapshot()
        self._generation = 0

    @staticmethod
    @lru_cache(maxsize=1)
    def available():
        return find_spec("aalink") is not None

    def snapshot(self):
        with self._lock:
            return self._snapshot

    def _publish(self, snapshot):
        with self._lock:
            self._snapshot = snapshot

    def start(self):
        with self._control:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._generation += 1
            self._publish(LinkSnapshot(monotonic(), "starting", revision=self._generation * 1000000))
            self._thread = Thread(target=self._run, name="ableton-link", daemon=True)
            self._thread.start()

    def _run(self):
        try:
            asyncio.run(self._poll())
        except Exception as exc:
            self._publish(LinkSnapshot(monotonic(), "error", error=str(exc)))

    async def _poll(self):
        backend = None
        revision = self._generation * 1000000
        previous = None
        try:
            backend = self._factory()
            while not self._stop.is_set():
                sample = backend.read()
                if sample:
                    at, tempo, beat, peers, cost = sample
                    if not (all(math.isfinite(v) for v in (at, tempo, beat, cost))
                            and 20 <= tempo <= 999 and peers >= 0 and cost < 100):
                        raise ValueError("Amostra Link inválida ou excessivamente lenta.")
                    state = "connected" if peers > 0 else "waiting"
                    if previous:
                        expected = previous.beat + (at - previous.updated_at) * previous.tempo / 60
                        if state != previous.state or abs(beat - expected) > .25:
                            revision += 1
                    previous = LinkSnapshot(at, state, tempo, beat, peers, revision, cost)
                    self._publish(previous)
                await asyncio.sleep(.02)
        finally:
            if backend is not None:
                backend.close()

    def stop(self):
        with self._control:
            self._stop.set()
            if self._thread:
                self._thread.join(3)
                if self._thread.is_alive():
                    raise RuntimeError("O módulo Link ainda está encerrando.")
            self._thread = None
            self._publish(LinkSnapshot(monotonic()))
