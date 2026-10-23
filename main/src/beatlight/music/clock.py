"""Projeção pura do relógio; usada no analisador e na apresentação entre blocos."""
from dataclasses import replace
import math
from beatlight.contracts import BeatSnapshot


def project_clock(snapshot: BeatSnapshot, at: float) -> BeatSnapshot:
    if not math.isfinite(at):
        raise ValueError("Tempo do relógio deve ser finito.")
    at = max(at, snapshot.updated_at)
    if snapshot.expires_at is not None and at >= snapshot.expires_at:
        return replace(snapshot, updated_at=at, state="unlocked", bpm=0.0,
                       period=0.0, phase=0.0, confidence=0.0,
                       last_beat_at=None, next_beat_at=None)
    if not snapshot.period or snapshot.last_reference_at is None:
        return replace(snapshot, updated_at=at)
    anchor = snapshot.last_beat_at
    cycles = (at - anchor) / snapshot.period
    whole = math.floor(cycles + 1e-9)
    phase = max(0.0, min(1.0, cycles - whole))
    last = anchor + whole * snapshot.period
    age = max(0.0, at - snapshot.last_reference_at)
    coast_after = 1.5 * snapshot.period
    decay = (math.exp(-max(0.0, age - coast_after) /
                     max(0.1, snapshot.expires_at - snapshot.last_reference_at - coast_after))
             if snapshot.expires_at is not None else
             max(0.4 / max(snapshot.reference_confidence, 0.4), math.exp(-age / 120)))
    state = "coasting" if age > coast_after and snapshot.state in ("locked", "coasting") else snapshot.state
    return replace(snapshot, updated_at=at, state=state, phase=phase,
                   beat_index=snapshot.beat_index + whole, last_beat_at=last,
                   next_beat_at=last + snapshot.period,
                   confidence=snapshot.reference_confidence * decay)
