"""Fila limitada com política explícita de priorização do áudio recente."""
from collections import deque
from threading import Condition
from beatlight.contracts import AudioBlock


class RecentBlockQueue:
    def __init__(self, capacity: int = 8):
        if capacity < 1:
            raise ValueError("A capacidade deve ser positiva.")
        self._items: deque[AudioBlock] = deque()
        self._capacity = capacity
        self._condition = Condition()
        self._dropped = 0

    def put(self, block: AudioBlock) -> None:
        with self._condition:
            if len(self._items) == self._capacity:
                self._items.popleft()
                self._dropped += 1
            self._items.append(block)
            self._condition.notify()

    def get(self, timeout: float = 0.1) -> AudioBlock | None:
        with self._condition:
            self._condition.wait_for(lambda: bool(self._items), timeout)
            return self._items.popleft() if self._items else None

    def reset(self) -> None:
        with self._condition:
            self._items.clear()
            self._dropped = 0

    def metrics(self) -> tuple[int, int]:
        with self._condition:
            return self._dropped, len(self._items)
