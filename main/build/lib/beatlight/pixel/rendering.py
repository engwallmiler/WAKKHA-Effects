"""Configuração gráfica antes da criação do renderer Chromium/Qt Quick.

O Pixel Studio é Canvas 2D. Composição por software evita corrupção de tiles
em drivers que falham ao compartilhar texturas entre Chromium e Qt.
"""
import os


def configure_renderer(environment=None):
    env=os.environ if environment is None else environment
    if env.get("BEATLIGHT_PIXEL_RENDERER", "software")=="gpu":
        return "gpu"
    flags=env.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    for option in ("--disable-gpu", "--disable-gpu-compositing"):
        if option not in flags.split():
            flags=(flags+" "+option).strip()
    env["QTWEBENGINE_CHROMIUM_FLAGS"]=flags
    env.setdefault("QT_QUICK_BACKEND", "software")
    return "software"
