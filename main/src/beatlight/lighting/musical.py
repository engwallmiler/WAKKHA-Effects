"""Perfis visuais do modo musical, independentes de renderização e amostras."""
from dataclasses import dataclass


def clamp(value, low=0.0, high=1.0):
    return min(high, max(low, value))


@dataclass(frozen=True, slots=True)
class MusicalProfile:
    movement_hz: float
    breathe_hz: float
    pan_span: float
    tilt_span: float
    white_mix: float


def visual_profile(structure, movement_limit):
    tension, energy, roll = structure.tension, structure.energy, structure.roll_strength
    beat_hz = 1 / clamp(structure.period or 0.5, 0.25, 1.2)
    ceiling = movement_limit * min(1.2, beat_hz * 0.45)
    if structure.state == "buildup":
        rise = clamp((tension - 0.2) / 0.75)
        rise = rise * rise * (3 - 2 * rise)
        return MusicalProfile(ceiling * clamp(0.25 + 0.65 * tension + 0.1 * roll),
            0.22 + 0.75 * tension + 0.8 * roll, 0.3 - 0.18 * tension,
            0.12, 0.12 + 0.85 * rise)
    if structure.state == "breakdown":
        return MusicalProfile(ceiling * (0.12 + 0.2 * tension),
            0.18 + 0.4 * tension, 0.28, 0.12, 0.08 * tension)
    if structure.state == "drop":
        return MusicalProfile(ceiling, 0.5, 0.42, 0.3, 0.05)
    return MusicalProfile(ceiling * (0.18 + 0.2 * energy),
        0.25, 0.25, 0.15, 0.08 * structure.brightness)
