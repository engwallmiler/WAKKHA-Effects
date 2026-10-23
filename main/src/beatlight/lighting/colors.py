"""Perfil automático explícito a partir de estrutura, energia e brilho do áudio."""
from beatlight.lighting.config import PALETTES


def automatic_colors(structure):
    if structure.state == "breakdown":
        return ((0.08, 0.22, 1.0), (0.3, 0.08, 0.7)), "auto · breakdown azul/violeta"
    if structure.state == "buildup":
        return ((0.25, 0.3, 1.0), (0.65, 0.18, 1.0)), "auto · build-up para branco"
    if structure.state == "drop":
        return ((1.0, 0.06, 0.12), (0.65, 0.08, 1.0)), "auto · drop vermelho/magenta"
    if structure.energy > 0.65:
        return PALETTES["red_blue"], "auto · groove de alta energia"
    if structure.brightness > 0.35:
        return PALETTES["amber_violet"], "auto · groove âmbar/violeta"
    return PALETTES["mint_blue"], "auto · groove menta/azul"


def automatic_texture_colors(texture):
    if texture.density > 0.65:
        return PALETTES["amber_violet"], "auto · textura densa âmbar/violeta"
    if texture.bass_level > 0.65 and texture.brightness < 0.2:
        return PALETTES["red_blue"], "auto · graves vermelho/azul"
    return PALETTES["mint_blue"], "auto · textura leve menta/azul"
