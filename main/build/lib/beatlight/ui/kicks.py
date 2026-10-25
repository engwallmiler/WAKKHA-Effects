"""Painel de inspeção de kicks; consome snapshots imutáveis, sem DSP na GUI."""
from time import monotonic
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QHBoxLayout, QVBoxLayout, QWidget, QPushButton,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QSizePolicy)
from beatlight.ui.components import card, label, metric, stable_label


class KickActivityWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(440, 190)
        self.snapshot = None
        self.active = False
        self.verification = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(QFont("Segoe UI", 9))
        area = QRectF(40, 14, max(1, self.width() - 58), max(1, self.height() - 48))
        p.fillRect(area, QColor("#11181d"))
        for value in (0, 0.25, 0.5, 0.75, 1):
            y = area.bottom() - value * area.height()
            p.setPen(QPen(QColor("#293640"), 1, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
            p.setPen(QColor("#8396a4"))
            p.drawText(QRectF(0, y - 9, 32, 18), Qt.AlignmentFlag.AlignRight, f"{value:g}")
        for seconds in (2, 1.5, 1, 0.5, 0):
            x = area.right() - seconds / 2 * area.width()
            p.setPen(QColor("#8396a4"))
            p.drawText(QRectF(x - 24, area.bottom() + 9, 48, 18), Qt.AlignmentFlag.AlignCenter, f"−{seconds:g}s" if seconds else "agora")
        snapshot = self.snapshot
        if snapshot and snapshot.history:
            now = snapshot.history[-1][0]
            def point(t, value):
                return QPointF(area.right() - (now - t) / 2 * area.width(),
                               area.bottom() - max(0, min(1, value)) * area.height())
            p.save()
            p.setClipRect(area)
            for index, color, style in ((1, "#6de9c1", Qt.PenStyle.SolidLine), (2, "#e5c482", Qt.PenStyle.DashLine)):
                path = QPainterPath()
                for i, item in enumerate(snapshot.history):
                    pos = point(item[0], item[index])
                    if i == 0:
                        path.moveTo(pos)
                    else:
                        path.lineTo(pos)
                ink = QColor(color)
                ink.setAlpha(235 if self.active else 80)
                p.setPen(QPen(ink, 2, style))
                p.drawPath(path)
            for kick in snapshot.events:
                if 0 <= now - kick.occurred_at <= 2:
                    x = point(kick.occurred_at, 0).x()
                    p.setPen(QPen(QColor("#7daeff"), 1, Qt.PenStyle.DotLine))
                    p.drawLine(QPointF(x, area.top()), QPointF(x, area.bottom()))
                    p.setBrush(QColor("#7daeff"))
                    p.drawEllipse(QPointF(x, area.top() + 7), 4, 4)
            if self.verification:
                for t, verdict in self.verification.slots:
                    if 0 <= now - t <= 2:
                        x = point(t, 0).x()
                        p.setPen(QPen(QColor("#f0c36a") if verdict != "confirmado" else QColor("#6de9c1"), 2))
                        p.drawLine(QPointF(x, area.bottom() - 16), QPointF(x, area.bottom()))
            p.restore()
        else:
            p.setPen(QColor("#9bacb8"))
            p.drawText(area, Qt.AlignmentFlag.AlignCenter, "Aguardando áudio para construir o histórico de kicks")
        p.end()


def build_kick_page(self):
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(14)
    toolbar = QHBoxLayout()
    self.kick_source = label("Selecione a entrada no Audio Monitor.", "subtitle", True)
    toolbar.addWidget(self.kick_source, 1)
    choose = QPushButton("Selecionar entrada →")
    choose.clicked.connect(lambda: self._navigate(0))
    toolbar.addWidget(choose)
    self.kick_start = QPushButton("▶  Iniciar")
    self.kick_start.setObjectName("primary")
    self.kick_start.clicked.connect(self._start)
    self.kick_stop = QPushButton("■  Parar")
    self.kick_stop.clicked.connect(self._stop_capture)
    toolbar.addWidget(self.kick_start)
    toolbar.addWidget(self.kick_stop)
    layout.addLayout(toolbar)
    row = QHBoxLayout()
    self.kick_metrics = {}
    for key, title, note in (("count", "CANDIDATOS GRAVES", "Saída bruta; pode incluir baixo"),
        ("intensity", "FORÇA DO ÚLTIMO KICK", "Relativa ao histórico recente"),
        ("confidence", "CONFIANÇA DO EVENTO", "Heurística, não probabilidade"),
        ("energy", "ENERGIA NA BANDA", "RMS filtrado em dBFS")):
        frame, value = metric(title, note)
        self.kick_metrics[key] = value
        row.addWidget(frame)
    layout.addLayout(row)
    confirmation_row = QHBoxLayout()
    self.kick_confirmation_metrics = {}
    for key, title, note in (("confirmed", "KICKS CONFIRMADOS", "Perfil de áudio e coerência temporal"),
        ("expected", "TEMPOS AVALIADOS", "Grade BPM; hipótese 4/4"),
        ("missing", "TEMPOS SEM KICK", "A previsão não cria eventos")):
        frame, value = metric(title, note)
        value.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        value.setFixedHeight(value.fontMetrics().lineSpacing() + 6)
        self.kick_confirmation_metrics[key] = value
        confirmation_row.addWidget(frame, 1)
    layout.addLayout(confirmation_row)
    self.kick_confirmation_detail = stable_label("Aguardando áudio para separar kick confirmado e janela prevista.", "muted", 2)
    layout.addWidget(self.kick_confirmation_detail)
    frame, contents = card()
    heading = QHBoxLayout()
    heading.addWidget(label("Atividade e limiar adaptativo", "section"))
    heading.addStretch()
    self.kick_badge = label("AGUARDANDO", "badge")
    heading.addWidget(self.kick_badge)
    contents.addLayout(heading)
    self.kick_plot = KickActivityWidget()
    contents.addWidget(self.kick_plot)
    contents.addWidget(label("<span style='color:#6de9c1'>● Atividade</span> &nbsp; <span style='color:#e5c482'>┄ Limiar</span> &nbsp; <span style='color:#7daeff'>● Candidatos graves</span> &nbsp; <span style='color:#6de9c1'>┃ Grade com kick</span> &nbsp; <span style='color:#f0c36a'>┃ Grade sem kick</span> &nbsp; · Últimos 2 segundos", "muted", True))
    self.kick_parameters = label("Banda 40–150 Hz · análise independente", "muted", True)
    contents.addWidget(self.kick_parameters)
    layout.addWidget(frame)
    frame, contents = card()
    event_row = QHBoxLayout()
    self.kick_indicator = label("SEM EVENTOS", "badge")
    self.kick_indicator.setMinimumWidth(150)
    self.kick_detail = label("Aguardando áudio.", "muted", True)
    event_row.addWidget(self.kick_indicator)
    event_row.addWidget(self.kick_detail, 1)
    contents.addLayout(event_row)
    self.kick_table = QTableWidget(0, 5)
    self.kick_table.setHorizontalHeaderLabels(("Há (tempo do áudio)", "Força relativa", "Confiança heurística", "Intervalo anterior", "Verificação"))
    self.kick_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    self.kick_table.verticalHeader().hide()
    self.kick_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    self.kick_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    self.kick_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    self.kick_table.setStyleSheet("QTableWidget { background: #11181d; color: #dce5e9; border: 0; gridline-color: #25313a; } QHeaderView::section { background: #1b252c; color: #a4b6c3; border: 0; padding: 6px; }")
    self.kick_table.setFixedHeight(150)
    self._kick_events_key = None
    contents.addWidget(self.kick_table)
    layout.addWidget(frame)
    self.kick_notice = label("Detector heurístico: compare com os kicks da faixa. Ajustes em Configurações; salve e reinicie a captura.", "notice", True)
    layout.addWidget(self.kick_notice)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(page)
    return scroll


def update_kick_view(self, snapshot, status, fresh):
    kicks = snapshot.kicks if snapshot else None
    verification = snapshot.kick_verification if snapshot and not snapshot.kick_verification_error else None
    self.kick_plot.verification = verification
    for key, value in self.kick_confirmation_metrics.items():
        count = getattr(verification, {"confirmed": "confirmed_count", "expected": "expected_count", "missing": "missed_count"}[key]) if verification else None
        value.setText(str(count) if count is not None else "—")
    grid = verification.grid if verification else None
    if grid and grid.state in ("tracking", "predicting"):
        self.kick_confirmation_detail.setText(f"Grade {60/grid.period:.1f} BPM · intervalo esperado {grid.period*1000:.0f} ms · confiança {grid.confidence:.0%} · {grid.state}\nPerfil rejeitou {verification.rejected_profile} candidatos; grade rejeitou {verification.rejected_grid}. Tempos previstos podem permanecer sem kick.")
    else:
        self.kick_confirmation_detail.setText("Confirmação acústica em aprendizado; aguardando grade confiável de BPM. Previsões não acionam pulsos.")
    self.kick_confirmation_detail.setToolTip(self.kick_confirmation_detail.text())
    self.kick_plot.snapshot = kicks
    self.kick_plot.active = fresh and kicks is not None
    if self.pages.currentIndex() == 4:
        self.kick_plot.update()
    self.kick_start.setEnabled(self.start_button.isEnabled())
    self.kick_stop.setEnabled(self.stop_button.isEnabled())
    self.kick_source.setText(("TESTE SINTÉTICO · " if self.source_combo.currentData() in ("synthetic", "structure_demo", "texture_demo") else "ENTRADA · ") + (self.device_combo.currentText() or "Nenhuma entrada selecionada"))
    self.kick_badge.setText("AO VIVO" if fresh and kicks and kicks.ready else "ADAPTANDO" if fresh else "ÚLTIMO RESULTADO" if kicks else "AGUARDANDO")
    self.kick_notice.setText("Falha de captura: " + status.error if status.error else
        "Detector indisponível: " + snapshot.kick_error if snapshot and snapshot.kick_error else
        "Compare os eventos com a faixa. Graves percussivos e baixos com ataque podem ser confundidos com kicks. Ajuste em Configurações, salve e reinicie a captura.")
    if not kicks:
        for value in self.kick_metrics.values():
            value.setText("—")
        self.kick_indicator.setText("SEM EVENTOS")
        self.kick_detail.setText("O detector precisa de cerca de 300 ms de áudio contínuo para adaptar o histórico.")
        self.kick_table.setRowCount(0)
        self._kick_events_key = None
        return
    self.kick_metrics["count"].setText(str(kicks.count))
    self.kick_metrics["energy"].setText(f"{kicks.band_db:.1f} dBFS")
    event = kicks.last_event
    self.kick_metrics["intensity"].setText(f"{event.intensity:.0%}" if event else "—")
    self.kick_metrics["confidence"].setText(f"{event.confidence:.0%}" if event else "—")
    confirmed = verification.confirmed_events[-1] if verification and verification.confirmed_events else None
    self.kick_indicator.setText("KICK CONFIRMADO" if confirmed and fresh and verification.last_confirmed_at is not None and monotonic() - verification.last_confirmed_at < 0.16 else "ESCUTANDO" if fresh and kicks.ready else "ADAPTANDO" if fresh else "PARADO")
    self.kick_parameters.setText(f"Banda {kicks.band_hz[0]:g}–{kicks.band_hz[1]:g} Hz · janela {kicks.window_ms:.1f} ms · passo {kicks.hop_ms:.1f} ms · parâmetros próprios do detector")
    self.kick_detail.setText(f"Ataque {kicks.attack:.2f} · fluxo grave {kicks.flux:.2f} · contraste {kicks.contrast:.1f}× · atividade {kicks.score:.2f} / limiar {kicks.threshold:.2f} · apoio rítmico {kicks.regularity:.0%}")
    # Os horários usam o tempo analisado, congelando corretamente ao parar.
    key = (kicks.frame_id, kicks.events, verification) if self.pages.currentIndex() == 4 else None
    if key is not None and key != self._kick_events_key:
        self._kick_events_key = key
        events = kicks.events[-8:]
        self.kick_table.setRowCount(len(events))
        for row, index in enumerate(range(len(events) - 1, -1, -1)):
            kick = events[index]
            interval = kick.occurred_at - events[index - 1].occurred_at if index > 0 else None
            confirmed_times = {e.occurred_at for e in verification.confirmed_events} if verification else set()
            acoustic_times = {e.occurred_at for e in verification.acoustic_events} if verification else set()
            verdict = ("CONFIRMADO" if kick.occurred_at in confirmed_times else "FORA DA GRADE" if kick.occurred_at in acoustic_times
                else "REJEITADO" if verification and verification.updated_at - kick.occurred_at >= 0.14 else "EM ANÁLISE")
            values = (f"{max(0, kicks.analyzed_at - kick.occurred_at):.2f} s", f"{kick.intensity:.0%}", f"{kick.confidence:.0%}", f"{interval * 1000:.0f} ms" if interval else "—", verdict)
            for col, value in enumerate(values):
                item = self.kick_table.item(row, col)
                if item is None:
                    item = QTableWidgetItem()
                    self.kick_table.setItem(row, col, item)
                item.setText(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
