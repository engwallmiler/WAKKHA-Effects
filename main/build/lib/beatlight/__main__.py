"""Ponto de entrada desktop: python -m beatlight."""
import argparse
from dataclasses import replace
from pathlib import Path
import sys
from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication
from beatlight.configuration.store import SettingsStore
from beatlight.diagnostics.logging import configure_logging
from beatlight.ui.theme import STYLE
from beatlight.ui.window import MainWindow


def main() -> int:
    parser = argparse.ArgumentParser(description="BEATLIGHT · Pixel Studio e sincronização musical")
    parser.add_argument("--synthetic", action="store_true", help="Selecionar sinal sintético de teste")
    parser.add_argument("--config-dir", type=Path, help="Diretório alternativo de preferências e logs")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("BEATLIGHT DMX")
    app.setOrganizationName("WAKKHA")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    icon = QPixmap(64, 64)
    icon.fill(QColor("#15191d"))
    painter = QPainter(icon)
    painter.setBrush(QColor("#6de9c1"))
    painter.setPen(QColor("#6de9c1"))
    for x, height in ((12, 20), (24, 40), (36, 30), (48, 15)):
        painter.drawRoundedRect(x, (64 - height) // 2, 6, height, 2, 2)
    painter.end()
    app.setWindowIcon(QIcon(icon))
    directory = args.config_dir or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    log_warning = configure_logging(directory / "logs")
    store = SettingsStore(directory / "preferences.json")
    settings = store.load()
    if args.synthetic:
        settings = replace(settings, source="synthetic", device_id="test:stereo")
    window = MainWindow(store, settings, "\n".join(x for x in (log_warning, store.warning) if x))
    window._navigate(9)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
