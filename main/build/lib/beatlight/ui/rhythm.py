"""Apresentação do relógio musical. Projeção temporal usa o contrato do tracker."""
import math
from time import monotonic
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QScrollArea, QProgressBar
from beatlight.music.clock import project_clock
from beatlight.music.grid import project_grid, grid_clock
from beatlight.ui.components import card, label, metric, stable_label

STATES = {"unlocked": "SEM SINCRONISMO", "acquiring": "ADQUIRINDO", "locked": "SINCRONIZADO", "coasting": "ESTIMADO"}


class BeatClockWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(220, 210)
        self.snapshot = None
        self.active = False

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(self.width() / 2, self.height() / 2 - 10)
        radius = min(self.width(), self.height() - 30) / 2 - 16
        circle = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        p.setPen(QPen(QColor("#293640"), 10))
        p.drawEllipse(circle)
        beat = self.snapshot
        running = bool(beat and beat.period and self.active)
        color = QColor("#e5c482" if beat and beat.state == "coasting" else "#6de9c1")
        if not running:
            color.setAlpha(65)
        if beat and beat.period:
            p.setPen(QPen(color, 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(circle, 90 * 16, -round(beat.phase * 360 * 16))
            angle = beat.phase * 2 * math.pi
            dot = center + QPointF(math.sin(angle) * radius, -math.cos(angle) * radius)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawEllipse(dot, 7, 7)
            flash = running and beat.phase < 0.12
            p.setPen(color if flash else QColor("#dce5e9"))
            p.setFont(QFont("Segoe UI", 29, QFont.Weight.Bold))
            p.drawText(QRectF(center.x() - radius, center.y() - 28, radius * 2, 50), Qt.AlignmentFlag.AlignCenter, str(beat.beat_index + 1))
        else:
            p.setPen(QColor("#8396a4"))
            p.setFont(QFont("Segoe UI", 29))
            p.drawText(circle, Qt.AlignmentFlag.AlignCenter, "—")
        p.setPen(QColor("#8396a4"))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(QRectF(0, self.height() - 24, self.width(), 22), Qt.AlignmentFlag.AlignCenter, "BATIDA RELATIVA · SEM POSIÇÃO DE COMPASSO")
        p.end()


class BeatGridWidget(QWidget):
    """Oito linhas fixas; cursor contínuo e ataques reais separados."""
    def __init__(self):
        super().__init__()
        self.setFixedHeight(92)
        self.grid = None
        self.events = ()
        self.active = False
        self.setAccessibleName("Grade local contínua com oito tempos e kicks observados")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#11181d"))
        grid = self.grid
        if not grid or grid.state not in ("tracking", "predicting"):
            p.setPen(QColor("#8396a4"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Aguardando quatro kicks regulares")
            p.end()
            return
        left, span = 20.0, max(1.0, self.width() - 40.0)
        current = (grid.beat_index - grid.phrase_origin) % 8
        start_index = grid.beat_index - current
        p.setFont(QFont("Segoe UI", 9))
        for i in range(9):
            x = left + span * i / 8
            p.setPen(QPen(QColor("#7daeff" if i % 4 == 0 else "#3c505e"), 2 if i % 4 == 0 else 1))
            p.drawLine(QPointF(x, 12), QPointF(x, 60))
            if i < 8:
                p.setPen(QColor("#a7b9c7"))
                p.drawText(QRectF(x, 65, span / 8, 20), Qt.AlignmentFlag.AlignCenter, str(i + 1))
        for kick in self.events:
            position = (kick.occurred_at - grid.anchor_at) / grid.period - start_index
            if 0 <= position < 8:
                p.setPen(QPen(QColor("#6de9c1"), 4))
                x = left + span * position / 8
                p.drawLine(QPointF(x, 42), QPointF(x, 58))
        x = left + span * (current + grid.phase) / 8
        p.setPen(QPen(QColor("#e5c482" if grid.state == "predicting" else "#6de9c1"), 2))
        p.drawLine(QPointF(x, 7), QPointF(x, 62))
        p.end()


class TempoHistoryWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(440, 140)
        self.snapshot = None
        self.active = False
        self.limits = (90, 160)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(QFont("Segoe UI", 9))
        area = QRectF(42, 12, max(1, self.width() - 62), max(1, self.height() - 40))
        p.fillRect(area, QColor("#11181d"))
        low, high = self.limits
        for bpm in (low, (low + high) / 2, high):
            y = area.bottom() - (bpm - low) / (high - low) * area.height()
            p.setPen(QPen(QColor("#293640"), 1, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
            p.setPen(QColor("#8396a4"))
            p.drawText(QRectF(0, y - 9, 34, 18), Qt.AlignmentFlag.AlignRight, f"{bpm:g}")
        beat = self.snapshot
        if beat:
            path = QPainterPath()
            started = False
            now = beat.updated_at
            for t, bpm, confidence in beat.history:
                if now - t > 15 or not bpm:
                    started = False
                    continue
                pos = QPointF(area.right() - (now - t) / 15 * area.width(), area.bottom() - (bpm - low) / (high - low) * area.height())
                if not started:
                    path.moveTo(pos)
                    started = True
                else:
                    path.lineTo(pos)
            ink = QColor("#7daeff")
            ink.setAlpha(235 if self.active else 75)
            p.save()
            p.setClipRect(area)
            p.setPen(QPen(ink, 2))
            p.drawPath(path)
            p.restore()
        p.setPen(QColor("#8396a4"))
        p.drawText(QRectF(area.left(), area.bottom() + 8, 120, 18), "−15 segundos")
        p.drawText(QRectF(area.right() - 80, area.bottom() + 8, 80, 18), Qt.AlignmentFlag.AlignRight, "agora")
        p.end()


def build_rhythm_page(self):
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(14)
    toolbar = QHBoxLayout()
    self.rhythm_source = label("Selecione a entrada no Audio Monitor.", "subtitle", True)
    toolbar.addWidget(self.rhythm_source, 1)
    choose = QPushButton("Selecionar entrada →")
    choose.clicked.connect(lambda: self._navigate(0))
    toolbar.addWidget(choose)
    self.rhythm_start = QPushButton("▶  Iniciar")
    self.rhythm_start.setObjectName("primary")
    self.rhythm_start.clicked.connect(self._start)
    self.rhythm_stop = QPushButton("■  Parar")
    self.rhythm_stop.clicked.connect(self._stop_capture)
    toolbar.addWidget(self.rhythm_start)
    toolbar.addWidget(self.rhythm_stop)
    layout.addLayout(toolbar)
    row = QHBoxLayout()
    self.rhythm_metrics = {}
    for key, title, note in (("bpm", "BPM DA GRADE", "Quatro kicks regulares adquirem a referência"),
        ("confidence", "CONFIANÇA DO SINCRONISMO", "Heurística; decai sem referência"),
        ("period", "PERÍODO DA BATIDA", "Relógio corrigido progressivamente"),
        ("next", "PRÓXIMA BATIDA", "Previsão no relógio de aquisição")):
        frame, value = metric(title, note)
        self.rhythm_metrics[key] = value
        row.addWidget(frame)
    layout.addLayout(row)
    frame, contents = card("Grade local · frase contínua", "Linhas: tempos previstos · cursor: fase · marcas verdes: kicks confirmados. Continua sem kick.")
    self.rhythm_grid = BeatGridWidget()
    contents.addWidget(self.rhythm_grid)
    layout.addWidget(frame)
    row = QHBoxLayout()
    frame, contents = card("Fase da batida")
    self.beat_clock = BeatClockWidget()
    contents.addWidget(self.beat_clock)
    row.addWidget(frame, 1)
    frame, contents = card()
    heading = QHBoxLayout()
    heading.addWidget(label("Estado do sincronismo", "section"))
    heading.addStretch()
    self.rhythm_badge = label("SEM SINCRONISMO", "badge")
    heading.addWidget(self.rhythm_badge)
    contents.addLayout(heading)
    self.rhythm_state_detail = label("Aguardando kicks para estimar o andamento.", "subtitle", True)
    contents.addWidget(self.rhythm_state_detail)
    self.rhythm_confidence_bar = QProgressBar()
    self.rhythm_confidence_bar.setRange(0, 1000)
    self.rhythm_confidence_bar.setTextVisible(False)
    self.rhythm_confidence_bar.setFixedHeight(6)
    contents.addWidget(self.rhythm_confidence_bar)
    self.rhythm_detail = label("São necessários vários kicks regulares para adquirir a referência.", "muted", True)
    contents.addWidget(self.rhythm_detail)
    contents.addStretch()
    row.addWidget(frame, 2)
    layout.addLayout(row)
    hypotheses = QHBoxLayout()
    self.rhythm_hypotheses = []
    for title in ("METADE", "HIPÓTESE ATIVA", "DOBRO"):
        frame, contents = card()
        contents.addWidget(label(title, "eyebrow"))
        value = label("—", "metric")
        detail = label("Aguardando hipótese", "muted", True)
        contents.addWidget(value)
        contents.addWidget(detail)
        self.rhythm_hypotheses.append((value, detail))
        hypotheses.addWidget(frame)
    layout.addLayout(hypotheses)
    frame, contents = card("Histórico do detector por áudio", "Últimos 15 segundos · diagnóstico acústico independente da grade")
    self.tempo_history = TempoHistoryWidget()
    contents.addWidget(self.tempo_history)
    layout.addWidget(frame)
    self.rhythm_notice = label("Compare o BPM e o pulso com o Traktor. Os limites de andamento e o tempo de previsão são ajustados em Configurações.", "notice", True)
    layout.addWidget(self.rhythm_notice)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(page)
    return scroll


def update_rhythm_view(self, snapshot, status):
    self.rhythm_start.setEnabled(self.start_button.isEnabled())
    self.rhythm_stop.setEnabled(self.stop_button.isEnabled())
    live = status.state == "running"
    at = monotonic() if live else snapshot.structure.updated_at if snapshot and snapshot.structure else snapshot.beat.updated_at if snapshot and snapshot.beat else 0.0
    original = snapshot.beat if snapshot and not snapshot.beat_error else None
    structure = snapshot.structure if snapshot and not snapshot.structure_error else None
    grid = project_grid(structure.grid, at) if structure and structure.grid else None
    beat = grid_clock(grid, at, original) or (project_clock(original, at) if original and live else original)
    self.rhythm_grid.grid = grid
    self.rhythm_grid.events = structure.confirmed_kicks if structure else ()
    self.rhythm_grid.active = live
    self.beat_clock.snapshot = beat
    raw = self.runtime.snapshot()
    self.tempo_history.snapshot = raw.beat if raw and not raw.beat_error else None
    self.beat_clock.active = self.tempo_history.active = live and bool(beat and beat.period)
    self.tempo_history.limits = (self.settings.beat_min_bpm, self.settings.beat_max_bpm)
    if self.pages.currentIndex() == 5:
        self.rhythm_grid.update()
        self.beat_clock.update()
        self.tempo_history.update()
    self.rhythm_source.setText(("TESTE SINTÉTICO · " if self.source_combo.currentData() in ("synthetic", "structure_demo", "texture_demo") else "ENTRADA · ") + (self.device_combo.currentText() or "Nenhuma entrada selecionada"))
    self.rhythm_notice.setText("Falha de captura: " + status.error if status.error else
        "Tracker indisponível: " + snapshot.beat_error if snapshot and snapshot.beat_error else
        ("Relógio externo Ableton Link. Kicks e estrutura continuam analisados pelo áudio." if snapshot and snapshot.timing_source == "link" else "Relógio local por áudio. Grade estimada continua sem kick. Configure sincronismo externo em Ableton Link."))
    if not beat:
        for value in self.rhythm_metrics.values():
            value.setText("—")
        self.rhythm_badge.setText("AGUARDANDO")
        self.rhythm_confidence_bar.setValue(0)
        self.rhythm_state_detail.setText("Inicie a captura para acompanhar o andamento.")
        self.rhythm_detail.setText("Referência: kicks detectados no áudio original.")
        for value, detail in self.rhythm_hypotheses:
            value.setText("—")
            detail.setText("Aguardando hipótese")
        return
    linked = snapshot.timing_source == "link"
    self.rhythm_badge.setText("ABLETON LINK" if linked and live else STATES[beat.state] if live else "PARADO · ÚLTIMO RESULTADO")
    self.rhythm_metrics["bpm"].setText(f"{beat.bpm:.1f}" if beat.bpm else "—")
    self.rhythm_metrics["confidence"].setText(f"{beat.confidence:.0%}")
    self.rhythm_metrics["period"].setText(f"{beat.period * 1000:.1f} ms" if beat.period else "—")
    self.rhythm_metrics["next"].setText(f"{max(0, beat.next_beat_at - beat.updated_at) * 1000:.0f} ms" if beat.next_beat_at else "—")
    self.rhythm_confidence_bar.setValue(round(beat.confidence * 1000))
    descriptions = {"unlocked": "Sem referência confiável. Aguardando kicks regulares.",
        "acquiring": "Coletando regularidade e ajustando o relógio musical.",
        "locked": "Grade local acompanhada por kicks. Desvios consistentes corrigem fase e BPM.",
        "coasting": "Sincronismo estimado: o relógio segue a previsão sem novos kicks alinhados."}
    self.rhythm_state_detail.setText(("BPM e fase seguem a sessão Link. O relógio não indica presença de kick nem posição da track." if linked else descriptions[beat.state]) if live else "Captura parada. Valores preservados; o relógio está congelado.")
    age = max(0, beat.updated_at - beat.last_reference_at) if beat.last_reference_at is not None else None
    self.rhythm_detail.setText(f"Erro do último ajuste: {beat.phase_error_ms:+.1f} ms · alinhados {beat.matched_kicks} · fora da grade {beat.rejected_kicks}"
        + (f"\nReferência há {age:.2f} s · " + (f"grade contínua · correções {grid.corrections}" if grid and grid.state in ("tracking", "predicting") else f"PLL limitado a {self.settings.beat_hold_seconds:g} s") if age is not None else "")
        + ("\nSem novos blocos de áudio; confiança e validade continuam sendo avaliadas." if live and status.audio_age >= 0.5 else "")
        + ("\nAmbiguidade rítmica: outra hipótese também explica os kicks." if beat.ambiguous and beat.bpm else ""))
    if linked:
        self.rhythm_detail.setText("Relógio compartilhado em ciclos de oito tempos; use Sincronizar 1/8 para marcar o início visual desejado. Histórico e hipóteses abaixo pertencem ao detector por áudio.")
    for index, pair in enumerate(self.rhythm_hypotheses):
        value, detail = pair
        if index >= len(beat.hypotheses) or not beat.bpm:
            value.setText("—")
            detail.setText("Sem hipótese ativa")
            continue
        hypothesis = beat.hypotheses[index]
        value.setText(f"{hypothesis.bpm:.1f} BPM" if beat.bpm else "—")
        detail.setText(f"Diagnóstico acústico: {hypothesis.score:.0%} · " + ("dentro da faixa" if hypothesis.in_range else "fora da faixa preferida") if beat.bpm else "Sem hipótese ativa")
