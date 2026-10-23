"""Apresentação do espectro e dos descritores; não realiza processamento DSP."""
import math
from time import monotonic
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget
from beatlight.contracts import SpectralSnapshot
from beatlight.ui.components import card, label, metric

COLORS = ("#6de9c1", "#7daeff", "#e5c482")


class SpectrumWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(440, 230)
        self.snapshot: SpectralSnapshot | None = None
        self.active = False

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        left, top, right, bottom = 45, 16, self.width() - 18, self.height() - 36
        width, height = right - left, bottom - top
        p.fillRect(QRectF(left, top, width, height), QColor("#11181d"))
        p.setFont(QFont("Segoe UI", 9))
        upper = min(20000, self.snapshot.sample_rate / 2) if self.snapshot else 20000
        def x_coord(hz):
            return left + math.log(hz / 20) / math.log(upper / 20) * width
        for db in (-96, -72, -48, -24, 0):
            y = bottom - (db + 96) / 96 * height
            p.setPen(QPen(QColor("#293640"), 1, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(left, y), QPointF(right, y))
            p.setPen(QColor("#8396a4"))
            p.drawText(QRectF(0, y - 9, left - 8, 18), Qt.AlignmentFlag.AlignRight, str(db))
        for hz in (20, 50, 100, 250, 500, 1000, 2000, 5000, 10000, 20000):
            if hz > upper:
                continue
            x = x_coord(hz)
            p.setPen(QPen(QColor("#24313a"), 1, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(x, top), QPointF(x, bottom))
            p.setPen(QColor("#8396a4"))
            text = f"{hz / 1000:g}k" if hz >= 1000 else str(hz)
            p.drawText(QRectF(x - 19, bottom + 10, 38, 18), Qt.AlignmentFlag.AlignCenter, text)
        if self.snapshot:
            snapshot = self.snapshot
            bar_width = max(1, width / len(snapshot.levels_db) - 1.5)
            for hz, db in zip(snapshot.frequencies_hz, snapshot.levels_db):
                band = 0 if hz < snapshot.band_ranges_hz[0][1] else 1 if hz < snapshot.band_ranges_hz[1][1] else 2
                y = bottom - max(0, min(1, (db + 96) / 96)) * height
                ink = QColor(COLORS[band])
                ink.setAlpha(230 if self.active else 70)
                gradient = QLinearGradient(0, bottom, 0, top)
                dim = QColor(ink)
                dim.setAlpha(35 if self.active else 15)
                gradient.setColorAt(0, dim)
                gradient.setColorAt(1, ink)
                p.fillRect(QRectF(x_coord(hz) - bar_width / 2, y, bar_width, bottom - y), gradient)
                p.setPen(QPen(ink, 1.5))
                p.drawLine(QPointF(x_coord(hz) - bar_width / 2, y), QPointF(x_coord(hz) + bar_width / 2, y))
        else:
            p.setPen(QColor("#9bacb8"))
            p.drawText(QRectF(left, top, width, height), Qt.AlignmentFlag.AlignCenter,
                       "O espectro aparece após preencher a janela de análise")
        p.end()


def build_spectral_page(self):
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(14)
    toolbar = QHBoxLayout()
    self.spectral_source = label("Selecione a entrada no Audio Monitor.", "subtitle")
    toolbar.addWidget(self.spectral_source, 1)
    choose = QPushButton("Selecionar entrada →")
    choose.clicked.connect(lambda: self._navigate(0))
    toolbar.addWidget(choose)
    self.spectral_start = QPushButton("▶  Iniciar")
    self.spectral_start.setObjectName("primary")
    self.spectral_start.clicked.connect(self._start)
    self.spectral_stop = QPushButton("■  Parar")
    self.spectral_stop.clicked.connect(self._stop_capture)
    toolbar.addWidget(self.spectral_start)
    toolbar.addWidget(self.spectral_stop)
    layout.addLayout(toolbar)
    row = QHBoxLayout()
    self.spectral_metrics = {}
    for key, title, note in (("peak", "FREQUÊNCIA DOMINANTE", "Estimativa na resolução da FFT"),
                             ("rms", "ENERGIA DE ANÁLISE", "RMS após o pré-processamento"),
                             ("events", "TRANSIENTES", "Ataques genéricos nesta sessão"),
                             ("window", "JANELA DE ANÁLISE", "Duração da janela FFT")):
        frame, value = metric(title, note)
        self.spectral_metrics[key] = value
        row.addWidget(frame)
    layout.addLayout(row)
    plot_card, plot_layout = card()
    heading = QHBoxLayout()
    heading.addWidget(label("Distribuição de frequências", "section"))
    heading.addStretch()
    self.spectral_badge = label("AGUARDANDO", "badge")
    heading.addWidget(self.spectral_badge)
    plot_layout.addLayout(heading)
    self.spectrum_plot = SpectrumWidget()
    plot_layout.addWidget(self.spectrum_plot, 1)
    self.spectral_detail = label("20 Hz – 20 kHz · escala logarítmica · níveis RMS em dBFS", "muted")
    plot_layout.addWidget(self.spectral_detail)
    layout.addWidget(plot_card, 1)
    bands = QHBoxLayout()
    self.band_values, self.band_shares, self.band_ranges, self.band_bars = [], [], [], []
    for name, color in zip(("GRAVES", "MÉDIOS", "AGUDOS"), COLORS):
        frame, contents = card()
        contents.addWidget(label(name, "eyebrow"))
        value = label("—", "metric")
        value.setStyleSheet("color: " + color + ";")
        contents.addWidget(value)
        bar = QProgressBar()
        bar.setRange(0, 1000)
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setFixedHeight(5)
        bar.setStyleSheet("QProgressBar { background: #10171b; border: 0; } QProgressBar::chunk { background: " + color + "; }")
        contents.addWidget(bar)
        share, freq = label("— da energia analisada", "muted"), label("— Hz", "muted")
        contents.addWidget(share)
        contents.addWidget(freq)
        self.band_values.append(value)
        self.band_shares.append(share)
        self.band_ranges.append(freq)
        self.band_bars.append(bar)
        bands.addWidget(frame)
    layout.addLayout(bands)
    event_card, event_layout = card()
    event_row = QHBoxLayout()
    self.transient_indicator = label("SEM EVENTOS", "badge")
    self.transient_indicator.setMinimumWidth(160)
    self.transient_detail = label("Transientes indicam mudanças abruptas no sinal. Abra Kick Monitor para os eventos de kick.", "muted", True)
    event_row.addWidget(self.transient_indicator)
    event_row.addWidget(self.transient_detail, 1)
    event_layout.addLayout(event_row)
    layout.addWidget(event_card)
    self.analysis_notice = label("Inicie a captura para analisar. Os filtros atuam nos dados de análise; a reprodução e os medidores de entrada preservam o sinal original.", "notice", True)
    layout.addWidget(self.analysis_notice)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(page)
    return scroll


def update_spectral_view(self, snapshot, status, fresh):
    spectrum = snapshot.spectral if snapshot else None
    self.spectrum_plot.snapshot, self.spectrum_plot.active = spectrum, fresh and spectrum is not None
    if self.pages.currentIndex() == 3:
        self.spectrum_plot.update()
    if status.error:
        self.analysis_notice.setText("Falha de captura: " + status.error)
    elif snapshot and snapshot.analysis_error:
        self.analysis_notice.setText("Análise indisponível: " + snapshot.analysis_error + ". A captura e os medidores permanecem ativos.")
    else:
        self.analysis_notice.setText("Filtros aplicados somente ao espectro. Transientes são ataques genéricos; a detecção específica está no Kick Monitor.")
    device = self.device_combo.currentText() or "Nenhuma entrada selecionada"
    test = self.source_combo.currentData() in ("synthetic", "structure_demo", "texture_demo")
    self.spectral_source.setText(("TESTE SINTÉTICO · " if test else "ENTRADA · ") + device)
    self.spectral_badge.setText("AO VIVO" if fresh and spectrum else "PREENCHENDO JANELA" if fresh else "ÚLTIMO RESULTADO" if spectrum else "AGUARDANDO")
    if spectrum is None:
        for value in self.spectral_metrics.values():
            value.setText("—")
        for value, share, bar in zip(self.band_values, self.band_shares, self.band_bars):
            value.setText("—")
            share.setText("— da energia analisada")
            bar.setValue(0)
        self.transient_indicator.setText("SEM EVENTOS")
        self.transient_detail.setText("Aguardando uma janela completa de análise.")
        return
    self.spectral_metrics["peak"].setText(f"{spectrum.dominant_hz:,.0f} Hz".replace(",", ".") if spectrum.dominant_hz else "—")
    self.spectral_metrics["rms"].setText(f"{spectrum.total_rms_db:.1f} dBFS")
    self.spectral_metrics["events"].setText(str(spectrum.transient_count))
    self.spectral_metrics["window"].setText(f"{spectrum.fft_size / spectrum.sample_rate * 1000:.1f} ms")
    self.spectral_detail.setText(f"Hann · {spectrum.fft_size} amostras · resolução {spectrum.sample_rate / spectrum.fft_size:.1f} Hz · passo {spectrum.hop_size / spectrum.sample_rate * 1000:.1f} ms · quadro {spectrum.frame_id}")
    for i, (low, high) in enumerate(spectrum.band_ranges_hz):
        high = min(high, spectrum.sample_rate / 2)
        self.band_values[i].setText(f"{spectrum.band_levels_db[i]:.1f} dBFS")
        self.band_shares[i].setText(f"{spectrum.band_fraction[i] * 100:.1f}% da energia analisada")
        self.band_ranges[i].setText(f"{low:g} – {high:g} Hz")
        self.band_bars[i].setValue(round(spectrum.band_fraction[i] * 1000))
    event = spectrum.last_transient
    recent = bool(event and fresh and monotonic() - event.detected_at < 0.2)
    self.transient_indicator.setText("ATAQUE DETECTADO" if recent else "ESCUTANDO" if fresh else "PARADO")
    self.transient_detail.setText(
        f"Fluxo {spectrum.spectral_flux:.3f} · atividade {spectrum.transient_score:.3f} · limiar adaptativo {spectrum.transient_threshold:.3f}"
        + (f" · último evento: confiança heurística {event.confidence:.0%}" if event else " · nenhum evento confirmado"))
