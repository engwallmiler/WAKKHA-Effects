"""Mistura RGBW abstrata; branco neutro ilustrativo, sem calibração de hardware."""
from dataclasses import replace


def preview_rgb(state):
    """Cor aparente antes do dimmer. O palco aplica intensity separadamente."""
    return tuple(min(1.0, c + state.white) for c in state.color)


def to_rgbw(state, white_capable=True, strength=1.0, explicit=False):
    if state.intensity == 0:
        return replace(state, color=(0.0, 0.0, 0.0), white=0.0)
    if not white_capable:
        return replace(state, color=preview_rgb(state), white=0.0)
    if explicit:
        return state
    # Transfere a parte comum ao emissor branco sem duplicar essa energia em RGB.
    shared = min(min(state.color) * strength, 1.0 - state.white)
    return replace(state, color=tuple(max(0.0, c - shared) for c in state.color), white=state.white + shared)
