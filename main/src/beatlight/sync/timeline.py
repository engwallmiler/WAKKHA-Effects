"""Projeção pura do relógio Link para as interfaces já usadas pelo palco."""
from dataclasses import replace
import math
from beatlight.contracts import KickGridSnapshot
from beatlight.music.grid import project_grid, grid_clock


def link_grid(link, at, offset_ms=0.0):
    if not math.isfinite(offset_ms) or not -250 <= offset_ms <= 250:
        raise ValueError("Compensação Link deve estar entre -250 e 250 ms.")
    if not link or not link.usable(at):
        return None
    period = 60 / link.tempo
    # Positivo atrasa o pulso visual. Monotonic é a base de tempo da captura.
    anchor = link.updated_at - link.beat * period + offset_ms / 1000
    grid = KickGridSnapshot(updated_at=at, state="tracking", period=period,
        anchor_at=anchor, confidence=1.0, last_reference_at=at,
        revision=1000000000 + link.revision * 1001 + round(offset_ms + 250),
        jitter_ms=link.sample_ms / 2, reference_confidence=1.0)
    return project_grid(grid, at)


def apply_link(snapshot, link, at, offset_ms=0.0):
    """Troca só o relógio efetivo; conserva todos os eventos e a análise acústica."""
    grid = link_grid(link, at, offset_ms)
    if snapshot is None or grid is None:
        return snapshot
    original = snapshot.beat
    beat = grid_clock(grid, at, original)
    structure = snapshot.structure
    if structure and not snapshot.structure_error:
        phrase = grid.beat_index % 8 + 1
        structure = replace(structure, grid=grid, period=grid.period,
            phrase_kick=phrase, bar_beat=(phrase - 1) % 4 + 1,
            phrase_bar=(phrase - 1) // 4 + 1, timing_source="link")
    return replace(snapshot, beat=beat, beat_error="", structure=structure,
        timing_source="link")
