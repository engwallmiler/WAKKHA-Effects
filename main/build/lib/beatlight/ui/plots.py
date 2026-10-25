"""Widgets desenham somente snapshots reduzidos; nenhum cálculo musical."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget
from beatlight.contracts import MonitorSnapshot

MINT = QColor("#6de9c1")
BLUE = QColor("#7daeff")


class WaveformWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(380, 230)
        self.snapshot: MonitorSnapshot | None = None
        self.active = False

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        width, height = self.width(), self.height()
        left, right, top, bottom = 38, width - 12, 18, height - 30
        p.fillRect(QRectF(left, top, right - left, bottom - top), QColor("#12181c"))
        p.setFont(QFont("Segoe UI", 9))
        for col in range(9):
            x = left + col * (right - left) / 8
            p.setPen(QPen(QColor("#253039"), 1, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(x, top), QPointF(x, bottom))
            p.setPen(QColor("#657582"))
            p.drawText(QRectF(x - (50 if col == 8 else 25), bottom + 9, 50, 20), Qt.AlignmentFlag.AlignCenter,
                       f"{col * 25 - 200} ms" if col < 8 else "agora")
        for channel, color in enumerate((MINT, BLUE)):
            center = top + (bottom - top) * (0.25 + channel * 0.5)
            amplitude = (bottom - top) * 0.21
            p.setPen(QColor("#8397a5"))
            p.drawText(QRectF(3, center - 10, 28, 20), Qt.AlignmentFlag.AlignCenter,
                       "L" if channel == 0 else "R")
            p.setPen(QPen(QColor("#34424c"), 1))
            p.drawLine(QPointF(left, center), QPointF(right, center))
            for offset in (-amplitude, amplitude):
                p.setPen(QPen(QColor("#202b32"), 1))
                p.drawLine(QPointF(left, center + offset), QPointF(right, center + offset))
            if self.snapshot and channel < len(self.snapshot.waveform):
                data = self.snapshot.waveform[channel]
                count = len(data) // 2
                ink = QColor(color)
                ink.setAlpha(220 if self.active else 65)
                p.setPen(QPen(ink, 1.35))
                for i in range(count):
                    x = left + i / max(1, count - 1) * (right - left)
                    low, high = data[i * 2:i * 2 + 2]
                    p.drawLine(QPointF(x, center - max(-1, min(1, high)) * amplitude),
                               QPointF(x, center - max(-1, min(1, low)) * amplitude + 0.5))
        if not self.snapshot:
            p.setPen(QColor("#93a3af"))
            p.drawText(QRectF(left, (top + bottom) / 2 - 15, right - left, 30),
                       Qt.AlignmentFlag.AlignCenter, "Inicie a captura para visualizar o sinal")
        p.end()


class StereoMeter(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(165, 230)
        self.snapshot: MonitorSnapshot | None = None
        self.active = False

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        top, bottom = 15, self.height() - 43
        bar_width = min(28, self.width() // 7)
        for channel, color in enumerate((MINT, BLUE)):
            x = self.width() * 0.28 + channel * (bar_width + 16)
            p.fillRect(QRectF(x, top, bar_width, bottom - top), QColor("#10171b"))
            rms, peak = -120.0, -120.0
            if self.active and self.snapshot and channel < len(self.snapshot.rms_db):
                rms, peak = self.snapshot.rms_db[channel], self.snapshot.peak_db[channel]
            ratio = max(0, min(1, (rms + 60) / 60))
            gradient = QLinearGradient(0, bottom, 0, top)
            gradient.setColorAt(0, color)
            gradient.setColorAt(0.82, QColor("#e4cb79"))
            gradient.setColorAt(1, QColor("#f38379"))
            p.fillRect(QRectF(x, bottom - ratio * (bottom - top), bar_width,
                             ratio * (bottom - top)), gradient)
            for db in range(-60, 1, 3):
                y = bottom - (db + 60) / 60 * (bottom - top)
                p.setPen(QPen(QColor("#192126"), 2))
                p.drawLine(QPointF(x, y), QPointF(x + bar_width, y))
            peak_y = bottom - max(0, min(1, (peak + 60) / 60)) * (bottom - top)
            p.setPen(QPen(QColor("#e3f1f7"), 2))
            p.drawLine(QPointF(x, peak_y), QPointF(x + bar_width, peak_y))
            p.setPen(color)
            p.drawText(QRectF(x - 8, bottom + 9, bar_width + 16, 20),
                       Qt.AlignmentFlag.AlignCenter, "L" if channel == 0 else "R")
        p.setPen(QColor("#7e909e"))
        p.setFont(QFont("Segoe UI", 8))
        for db in (0, -12, -24, -36, -48, -60):
            y = bottom - (db + 60) / 60 * (bottom - top)
            p.drawText(QRectF(3, y - 8, 30, 16), Qt.AlignmentFlag.AlignRight, str(db))
        p.end()
