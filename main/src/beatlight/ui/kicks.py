"""Painel de inspeção de kicks; consome snapshots imutáveis, sem DSP na GUI."""
from time import monotonic
import math
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
            for index,color,style in ((1,'#b496ff',Qt.PenStyle.SolidLine),(2,'#df99c9',Qt.PenStyle.DashLine)):
                path=QPainterPath()
                for i,item in enumerate(snapshot.masked_history):
                    pos=point(item[0],item[index])
                    path.moveTo(pos) if i==0 else path.lineTo(pos)
                ink=QColor(color);ink.setAlpha(220 if self.active else 70);p.setPen(QPen(ink,1.5,style));p.drawPath(path)
            confirmed_times={event.occurred_at for event in self.verification.confirmed_events} if self.verification else set()
            grid = self.verification.grid if self.verification else None
            if grid and grid.period and grid.anchor_at is not None:
                first = math.ceil((now - 2 - grid.anchor_at) / grid.period)
                for index in range(first, first + math.ceil(2 / grid.period) + 1):
                    target = grid.anchor_at + index * grid.period
                    if target > now:
                        break
                    x = point(target, 0).x()
                    p.setPen(QPen(QColor('#40515d'), 1, Qt.PenStyle.DashLine))
                    p.drawLine(QPointF(x, area.top()), QPointF(x, area.bottom()))
            peak_grid = self.verification.peak_grid if self.verification else None
            if peak_grid and peak_grid.period and peak_grid.anchor_at is not None:
                first = math.ceil((now-2-peak_grid.anchor_at)/peak_grid.period)
                for index in range(first, first+math.ceil(2/peak_grid.period)+1):
                    target = peak_grid.anchor_at+index*peak_grid.period
                    if target>now:
                        break
                    x = point(target,0).x()
                    p.setPen(QPen(QColor('#6cbdf6'),1,Qt.PenStyle.DotLine))
                    p.drawLine(QPointF(x,area.top()),QPointF(x,area.bottom()))
            events = {kick.occurred_at: kick for kick in snapshot.events}
            if self.verification:
                events.update((kick.occurred_at, kick) for kick in self.verification.confirmed_events)
            for kick in events.values():
                if 0 <= now - kick.occurred_at <= 2:
                    x = point(kick.occurred_at, 0).x()
                    confirmed = kick.occurred_at in confirmed_times
                    p.setPen(QPen(QColor('#65edaf' if confirmed else '#8396a4'), 2 if confirmed else 1))
                    p.drawLine(QPointF(x, area.top() if confirmed else area.bottom()-7), QPointF(x, area.bottom()))
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
    self.kick_grid_settings = QPushButton('BPM e grade →')
    def open_grid_settings():
        self._navigate(2)
        self.pages.widget(2).ensureWidgetVisible(self.beat_mode_combo, 50, 50)
    self.kick_grid_settings.clicked.connect(open_grid_settings)
    toolbar.addWidget(self.kick_grid_settings)
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
        ("intensity", "FORÇA DO CANDIDATO", "Relativa ao histórico; não é potência isolada do kick"),
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
    self.kick_confirmation_detail = stable_label("Aguardando áudio para separar kick confirmado e janela prevista.", "muted", 4)
    layout.addWidget(self.kick_confirmation_detail)
    frame, contents = card()
    heading = QHBoxLayout()
    heading.addWidget(label("Energia e novidade espectral · dois caminhos de ataque", "section"))
    heading.addStretch()
    self.kick_badge = label("AGUARDANDO", "badge")
    heading.addWidget(self.kick_badge)
    contents.addLayout(heading)
    self.kick_plot = KickActivityWidget()
    contents.addWidget(self.kick_plot)
    contents.addWidget(label("<span style='color:#6de9c1'>● Ataque por energia</span> · <span style='color:#e5c482'>┄ Seu limiar</span> · <span style='color:#b496ff'>● Novidade espectral</span> · <span style='color:#df99c9'>┄ Seu limiar</span><br><span style='color:#65edaf'>┃ Kick confirmado</span> · <span style='color:#8396a4'>╵ Candidato bruto (base)</span> · <span style='color:#8396a4'>┊ Grade de tempo</span> · <span style='color:#6cbdf6'>┊ Grade de picos reais</span> · <span style='color:#f0c36a'>┃ Tempo sem kick (base)</span> · Últimos 2 segundos", "muted", True))
    self.kick_parameters = stable_label("Banda 40–150 Hz · análise independente", "muted", 2)
    contents.addWidget(self.kick_parameters)
    layout.addWidget(frame)
    frame, contents = card()
    event_row = QHBoxLayout()
    self.kick_indicator = label("SEM EVENTOS", "badge")
    self.kick_indicator.setMinimumWidth(150)
    self.kick_detail = stable_label("Aguardando áudio.", "muted", 3)
    event_row.addWidget(self.kick_indicator)
    event_row.addWidget(self.kick_detail, 1)
    contents.addLayout(event_row)
    self.kick_table = QTableWidget(0, 6)
    self.kick_table.setHorizontalHeaderLabels(("Há (tempo do áudio)", "Força relativa", "Confiança heurística", "Intervalo anterior", "Sensor", "Verificação"))
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
        bpm = f'{60/grid.period:.0f}' if grid.tempo_locked and grid.tempo_mode in ('integer','manual') else f'{60/grid.period:.1f}'
        mode = 'BPM fixo' if grid.tempo_mode=='manual' else 'inteiro estabilizado' if grid.tempo_mode=='integer' and grid.tempo_locked else 'estabilizando o BPM inteiro' if grid.tempo_mode=='integer' else 'contínuo'
        self.kick_confirmation_detail.setText(f"Grade {bpm} BPM · {mode} · intervalo {grid.period*1000:.0f} ms · confiança {grid.confidence:.0%}\nPerfil rejeitou {verification.rejected_profile}; grade rejeitou {verification.rejected_grid}. A previsão não cria kicks.")
    else:
        self.kick_confirmation_detail.setText("Confirmação acústica em aprendizado; aguardando grade confiável de BPM. Previsões não acionam pulsos.")
    peak_grid = verification.peak_grid if verification else None
    if peak_grid:
        detail = (f"Grade auxiliar de máximos: {peak_grid.references}/3 referências; o reaprendizado do perfil funciona independentemente." if peak_grid.anchor_at is None else
            f"Grade de picos · {'prevendo, sem ataque recente' if peak_grid.state=='predicting' else 'acompanhando'} · espectro {peak_grid.spectral_similarity:.0%} · forma {peak_grid.envelope_similarity:.0%} · potência {peak_grid.power_ratio:.2f}× · desvio {peak_grid.phase_error_ms:+.0f} ms")
        self.kick_confirmation_detail.setText(self.kick_confirmation_detail.text()+"\n"+detail)
    recovery = verification.kick_recovery if verification else None
    if recovery:
        recovery_state = (f"Perfil recorrente ativo · reaprendizados {recovery.relearns}" if recovery.relearns and not recovery.progress else
            f"Reaprendendo perfil {recovery.progress}/{recovery.required} · reaprendizados {recovery.relearns}")
        self.kick_confirmation_detail.setText(self.kick_confirmation_detail.text()+
            f"\n{recovery_state} · {recovery.decision} {recovery.reason}")
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
    self.kick_parameters.setText(f"Banda {kicks.band_hz[0]:g}–{kicks.band_hz[1]:g} Hz · janela {kicks.window_ms:.1f} ms · passo {kicks.hop_ms:.1f} ms · "
        + (f'prioridade na grade · {kicks.offgrid_count} ataques fora dela' if kicks.grid_guided else 'aquisição acústica · sem prioridade da grade'))
    self.kick_detail.setText(f"Ataque {kicks.attack:.2f} · contraste {kicks.contrast:.1f}× · energia {kicks.score:.2f}/{kicks.threshold:.2f} · novidade {kicks.masked_score:.2f}/{kicks.masked_threshold:.2f}. O baixo pode reduzir o contraste sem apagar o novo ataque espectral.")
    # Os horários usam o tempo analisado, congelando corretamente ao parar.
    key = (kicks.frame_id, kicks.events, verification) if self.pages.currentIndex() == 4 else None
    if key is not None and key != self._kick_events_key:
        self._kick_events_key = key
        combined = {e.occurred_at:e for e in kicks.events}
        if verification:
            combined.update((e.occurred_at,e) for e in verification.confirmed_events)
        events = sorted(combined.values(),key=lambda e:e.occurred_at)[-8:]
        self.kick_table.setRowCount(len(events))
        for row, index in enumerate(range(len(events) - 1, -1, -1)):
            kick = events[index]
            interval = kick.occurred_at - events[index - 1].occurred_at if index > 0 else None
            confirmed_times = {e.occurred_at for e in verification.confirmed_events} if verification else set()
            acoustic_times = {e.occurred_at for e in verification.acoustic_events} if verification else set()
            verdict = ("CONFIRMADO" if kick.occurred_at in confirmed_times else "FORA DA GRADE" if kick.occurred_at in acoustic_times
                else "REJEITADO" if verification and verification.updated_at - kick.occurred_at >= 0.14 else "EM ANÁLISE")
            values = (f"{max(0, kicks.analyzed_at - kick.occurred_at):.2f} s", f"{kick.intensity:.0%}", f"{kick.confidence:.0%}", f"{interval * 1000:.0f} ms" if interval else "—", {'spectral':'Espectral','grid':'Grade + áudio','grid-peak':'Pico + BPM','grid-profile':'Perfil + grade'}.get(kick.evidence,'Energia'),verdict)
            for col, value in enumerate(values):
                item = self.kick_table.item(row, col)
                if item is None:
                    item = QTableWidgetItem()
                    self.kick_table.setItem(row, col, item)
                item.setText(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
