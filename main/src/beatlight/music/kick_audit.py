"""Inspeção causal: candidato acústico, kick coerente e posição esperada são distintos."""
from collections import deque
import math
from beatlight.contracts import KickVerificationSnapshot


class KickAudit:
    def __init__(self):
        self.confirmed_count = self.acoustic_count = 0
        self.confirmed_cursor = self.acoustic_cursor = -math.inf
        self.expected = self.matched = self.missed = 0
        self.slots = deque(maxlen=16)
        self.last_confirmed_at = None
        self.revision = None
        self.origin = None
        self.slot_index = None

    def process(self, structure, raw_events):
        at, grid = structure.updated_at, structure.grid
        for event in structure.confirmed_kicks:
            if event.occurred_at > self.confirmed_cursor:
                self.confirmed_count += 1
                self.confirmed_cursor = event.occurred_at
                self.last_confirmed_at = at
        for event in structure.acoustic_kicks:
            if event.occurred_at > self.acoustic_cursor:
                self.acoustic_count += 1
                self.acoustic_cursor = event.occurred_at
        if grid and grid.state in ("tracking", "predicting"):
            if self.origin is None or self.revision != grid.revision:
                self.revision = grid.revision
                self.slots.clear()
                self.origin = grid.anchor_at
                self.slot_index = math.floor((at - self.origin) / grid.period)
            # Espera 200 ms para permitir a confirmação acústica causal.
            due = math.floor((at - grid.anchor_at - 0.2) / grid.period + 1e-8)
            while self.slot_index <= due:
                target = grid.anchor_at + self.slot_index * grid.period
                tolerance = grid.period * 0.18
                confirmed = any(abs(e.occurred_at - target) <= tolerance for e in structure.confirmed_kicks)
                candidate = any(abs(e.occurred_at - target) <= tolerance for e in raw_events)
                self.expected += 1
                self.matched += int(confirmed)
                self.missed += int(not confirmed)
                self.slots.append((target, "confirmado" if confirmed else "grave rejeitado" if candidate else "sem kick"))
                self.slot_index += 1
        else:
            self.origin = self.slot_index = None
        return KickVerificationSnapshot(at, self.confirmed_count, self.acoustic_count,
            self.expected, self.matched, self.missed, structure.confirmed_kicks, structure.acoustic_kicks,
            tuple(self.slots), grid, structure.rejected_timbre, grid.rejected_offgrid if grid else 0, self.last_confirmed_at)
