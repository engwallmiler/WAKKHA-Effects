"""Alinhamento do ciclo visual de oito tempos, sem alterar o relógio acústico."""
import math


class PhraseClock:
    def __init__(self):
        self._last_command = 0
        self.reset()

    def reset(self):
        self._offset = 0.0
        self.manual = False
        self._key = None
        self._last_at = None

    def project(self, beat, grid, controls, at, active=True):
        valid = active and beat and beat.period and beat.state in ("locked", "coasting") and beat.confidence >= .35
        if not valid:
            self.reset()
            self._last_command = controls.phrase_sync_id
            return None
        key = (grid.revision, grid.phrase_origin) if grid else (0, 0)
        if self._key is not None and (key != self._key or at - self._last_at > .6):
            self.reset()
        self._key, self._last_at = key, at
        base = beat.beat_index + beat.phase - (grid.phrase_origin if grid else 0)
        if controls.phrase_sync_id != self._last_command:
            sync_at = controls.phrase_sync_at
            delta = at-sync_at if sync_at is not None else None
            # O worker pode ter lido seu tempo um instante antes do clique e
            # receber o comando novo ao adquirir o lock. Consuma no quadro seguinte.
            waiting = delta is not None and -.6 <= delta < 0
            if not waiting:
                self._last_command = controls.phrase_sync_id
                if delta is not None and 0 <= delta < .6:
                    self._offset = base-delta/beat.period
                    self.manual = True
        position = base - self._offset
        return max(0.0, position) if self.manual and position > -1e-6 else position

    @property
    def command(self):
        return self._last_command
