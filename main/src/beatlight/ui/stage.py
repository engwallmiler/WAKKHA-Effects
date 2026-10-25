"""Palco 2D: recebe somente estados abstratos; não interpreta áudio."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QPolygonF, QRadialGradient
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QPushButton, QProgressBar, QScrollArea, QSizePolicy, QVBoxLayout, QWidget
from beatlight.ui.components import card, label, metric, stable_label
from beatlight.ui.lighting import STATUS_NAMES, sync_phrase, can_sync_phrase
from beatlight.lighting.rgbw import preview_rgb
from beatlight.lighting.phrase import MOTIF_NAMES
from beatlight.music.grid import project_grid

STRUCTURE_NAMES = {"warming": "ANALISANDO", "groove": "GROOVE", "breakdown": "BREAKDOWN", "buildup": "BUILD-UP", "drop": "DROP", "silence": "SILÊNCIO"}


class StageView(QWidget):
    def __init__(self, fixtures, parent=None):
        super().__init__(parent)
        self.fixtures = tuple(fixtures)
        self.snapshot = None
        self.setMinimumSize(560, 300)
        self.setAccessibleName("Simulador de palco com quatro PARs e dois moving heads")

    def set_snapshot(self, snapshot):
        self.snapshot = snapshot
        if self.isVisible():
            self.update()

    @staticmethod
    def beam_target(index, kind, state):
        """Projeção normalizada ilustrativa, sem afirmar ângulos de um aparelho real."""
        xs = (230, 410, 590, 770, 100, 900)
        x = xs[index]
        return QPointF(x + (state.pan - 0.5) * 600 if kind == "moving_head" else x,
                       340 + state.tilt * 160 if kind == "moving_head" else 420)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#080e14"))
        scale = min(self.width() / 1000, self.height() / 510)
        painter.translate((self.width() - 1000 * scale) / 2, (self.height() - 510 * scale) / 2)
        painter.scale(scale, scale)
        painter.setPen(QColor("#253341"))
        painter.drawLine(40, 330, 960, 330)
        for y in (350, 390, 440, 500):
            painter.drawLine(20, y, 980, y)
        for x in range(0, 1001, 100):
            painter.drawLine(QPointF(500 + (x - 500) * 0.55, 330), QPointF(x, 510))
        painter.setPen(QPen(QColor("#374957"), 3))
        painter.drawLine(65, 65, 935, 65)
        painter.setPen(QPen(QColor("#1f2d39"), 1))
        painter.drawLine(65, 80, 935, 80)
        for x in range(65, 930, 40):
            painter.drawLine(x, 65, x + 20, 80)
            painter.drawLine(x + 20, 80, x + 40, 65)
        states = {s.fixture_id: s for s in self.snapshot.states} if self.snapshot else {}
        xs = (230, 410, 590, 770, 100, 900)
        for index, fixture in enumerate(self.fixtures):
            x, y = xs[index % len(xs)], 110
            state = states.get(fixture.fixture_id)
            intensity = state.intensity if state else 0.0
            color = QColor.fromRgbF(*preview_rgb(state)) if state else QColor("#33434f")
            if state and intensity > 0:
                target = self.beam_target(index % len(xs), fixture.kind, state)
                width = 62 if fixture.kind == "par" else 36
                gradient = QLinearGradient(QPointF(x, y), target)
                top = QColor(color)
                top.setAlphaF(intensity * 0.5)
                bottom = QColor(color)
                bottom.setAlphaF(intensity * 0.03)
                gradient.setColorAt(0, top)
                gradient.setColorAt(1, bottom)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(gradient)
                painter.drawPolygon(QPolygonF([QPointF(x - 7, y + 10), QPointF(x + 7, y + 10),
                    QPointF(target.x() + width, target.y()), QPointF(target.x() - width, target.y())]))
                center = QColor(color)
                center.setAlphaF(intensity * 0.65)
                edge = QColor(color)
                edge.setAlpha(0)
                painter.save()
                painter.translate(target)
                painter.scale(1, 0.3)
                # Gradiente local permite uma poça elíptica de luz sobre o piso.
                local = QRadialGradient(QPointF(0, 0), width * 1.7)
                local.setColorAt(0, center)
                local.setColorAt(1, edge)
                painter.setBrush(local)
                painter.drawEllipse(QPointF(0, 0), width * 1.7, width * 1.7)
                painter.restore()
            painter.setPen(QPen(QColor("#536674"), 2))
            painter.drawLine(x, 80, x, 94)
            painter.setBrush(QColor("#18232d"))
            painter.drawRoundedRect(QRectF(x - 19, y - 17, 38, 29), 6, 6)
            lens = QColor.fromRgbF(*(c * intensity for c in preview_rgb(state))) if state and intensity > .01 else QColor("#25333e")
            painter.setBrush(lens)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x, y + 9), 10, 5)
            painter.setPen(QColor("#a7b9c7"))
            painter.drawText(QRectF(x - 60, 29, 120, 24), Qt.AlignmentFlag.AlignCenter, fixture.name)
            painter.setPen(QColor("#758a9a"))
            painter.drawText(QRectF(x - 45, 145, 90, 22), Qt.AlignmentFlag.AlignCenter, f"{intensity:.0%}")
        painter.setPen(QColor("#526574"))
        painter.drawText(QRectF(30, 470, 940, 24), Qt.AlignmentFlag.AlignCenter,
                         "PALCO VIRTUAL  /  PROJEÇÃO 2D ILUSTRATIVA  /  SEM SAÍDA DMX")
        painter.end()


class ParPatternView(QWidget):
    """Mostra os disparos de quatro PARs nas 16 colcheias de um ciclo."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.snapshot = None
        self.setFixedHeight(76)
        self.setAccessibleName("Ritmo dos quatro PARs em oito tempos")
        self.setToolTip("Cada linha é um PAR; cada tempo tem duas colcheias. Blocos indicam disparos previstos pelo desenho atual.")

    def set_snapshot(self, snapshot):
        self.snapshot = snapshot
        self.update()

    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        light=self.snapshot
        masks=light.show_masks if light else ()
        phase=(light.phrase_step-1+light.phrase_phase) if light and light.phrase_step else (light.show_step-1+light.show_phase if light and light.show_step else -1)
        slot=int(phase*2)%16 if phase>=0 else -1
        left=62
        width=(self.width()-left)/16
        p.setPen(Qt.PenStyle.NoPen)
        for row in range(4):
            p.setPen(QColor("#8fa7b5"))
            p.drawText(QRectF(0,row*18,58,18),Qt.AlignmentFlag.AlignVCenter,f"PAR {row+1:02}")
            p.setPen(Qt.PenStyle.NoPen)
            for col in range(16):
                if light and light.breakdown_calm:
                    continue
                active=len(masks)==16 and bool(masks[col]&(1<<row))
                color=QColor("#66d9b8" if active else "#182731")
                if col==slot and active:color=QColor("#ffffff")
                p.setBrush(color)
                p.drawRoundedRect(QRectF(left+col*width+1,row*18+2,width-3,13),2,2)
        if light and light.breakdown_calm:
            for row,state in enumerate(light.states[:4]):
                gradient=QLinearGradient(left,0,self.width(),0)
                color=QColor.fromRgbF(*preview_rgb(state))
                color.setAlphaF(min(1.0,state.intensity*3))
                gradient.setColorAt(0,QColor("#182731"))
                gradient.setColorAt(.5,color)
                gradient.setColorAt(1,QColor("#182731"))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(gradient)
                p.drawRoundedRect(QRectF(left,row*18+2,self.width()-left-2,13),3,3)
        if slot>=0 and masks:
            p.setPen(QPen(QColor("#e9f7f3"),1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(left+slot*width,0,width,72))
        p.end()


def set_phrase_show(self, enabled):
    self.light_effect_combo.setCurrentIndex(self.light_effect_combo.findData("phrase_show" if enabled else "orchestrated_show"))


def build_stage_page(self):
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    row = QHBoxLayout()
    self.stage_status = stable_label("Motor desativado", "subtitle", 2)
    row.addWidget(self.stage_status, 1)
    self.stage_music_button = QPushButton("Usar automação musical")
    self.stage_music_button.clicked.connect(lambda: self.light_effect_combo.setCurrentIndex(self.light_effect_combo.findData("musical")))
    self.stage_show_button = QPushButton("Show de 8 · DESLIGADO")
    self.stage_show_button.setCheckable(True)
    self.stage_show_button.setChecked(self.light_effect_combo.currentData()=="phrase_show")
    self.stage_show_button.setToolTip("Liga os ritmos de oito tempos nos PARs. Desligado, usa o Show RGBW contínuo.")
    self.stage_show_button.toggled.connect(lambda enabled: set_phrase_show(self,enabled))
    row.addWidget(self.stage_show_button)
    self.stage_phrase_button = self.stage_show_button
    self.stage_sync_button = QPushButton("Sincronizar 1/8")
    self.stage_sync_button.setToolTip("Clique no primeiro tempo desejado. Ativa o show de oito e alinha o ciclo visual, preservando o BPM.")
    self.stage_sync_button.clicked.connect(lambda: sync_phrase(self))
    row.addWidget(self.stage_sync_button)
    self.stage_arm_button = QPushButton("Ativar motor")
    self.stage_arm_button.setCheckable(True)
    self.stage_arm_button.toggled.connect(self.light_arm_check.setChecked)
    row.addWidget(self.stage_arm_button)
    self.stage_blackout_button = QPushButton("BLACKOUT")
    self.stage_blackout_button.setObjectName("stop")
    self.stage_blackout_button.setCheckable(True)
    self.stage_blackout_button.toggled.connect(self.light_blackout_button.setChecked)
    row.addWidget(self.stage_blackout_button)
    for button, names in ((self.stage_show_button, ("Show de 8 · DESLIGADO", "Show de 8 · LIGADO")), (self.stage_music_button, ("Usar automação musical",)),
        (self.stage_arm_button, ("Ativar motor", "Desativar motor")),
        (self.stage_blackout_button, ("BLACKOUT", "LIBERAR BLACKOUT"))):
        button.ensurePolished()
        original = button.text()
        widths = []
        for name in names:
            button.setText(name)
            widths.append(button.sizeHint().width())
        button.setText(original)
        button.setFixedWidth(max(widths))
    layout.addLayout(row)
    row = QHBoxLayout()
    self.structure_metrics = {}
    for key, title, note in (("state", "ESTRUTURA MUSICAL", "Leitura heurística do áudio original"),
        ("tension", "TENSÃO", "Agudos, repetição e aceleração"),
        ("confidence", "CONFIANÇA", "Indicador; não probabilidade"),
        ("drop", "PÓS-DROP", "Alta energia por oito kicks")):
        frame, value = metric(title, note)
        value.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        value.setFixedHeight(value.fontMetrics().lineSpacing() + 6)
        frame.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        frame.setFixedHeight(value.height() + self.fontMetrics().lineSpacing() * 3 + 62)
        self.structure_metrics[key] = value
        row.addWidget(frame, 1)
    self.structure_metrics["state"].setStyleSheet("font-size: 20px;")
    layout.addLayout(row)
    texture_row = QHBoxLayout()
    self.texture_meters = {}
    for key, text in (("bass_level", "Graves"), ("density", "Densidade")):
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setFormat(text + " %p%")
        bar.setFixedHeight(24)
        bar.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.texture_meters[key] = bar
        texture_row.addWidget(bar, 1)
    self.texture_detail = stable_label("Áudio: aguardando descritores.", "muted")
    texture_row.addWidget(self.texture_detail, 2)
    layout.addLayout(texture_row)
    self.stage_view = StageView(self.light_runtime.engine.fixtures)
    self.stage_phrase_info = stable_label("Ciclo: aguardando grade.", "subtitle", 2)
    layout.addWidget(self.stage_phrase_info)
    pattern_row=QHBoxLayout()
    pattern_row.addWidget(label("Ritmo dos PARs", "muted"))
    self.stage_pattern_combo=QComboBox()
    for index in range(self.light_pattern_combo.count()):
        self.stage_pattern_combo.addItem(self.light_pattern_combo.itemText(index),self.light_pattern_combo.itemData(index))
    self.stage_pattern_combo.setCurrentIndex(self.stage_pattern_combo.findData(self.light_pattern_combo.currentData()))
    self.stage_pattern_combo.currentIndexChanged.connect(lambda: self.light_pattern_combo.setCurrentIndex(
        self.light_pattern_combo.findData(self.stage_pattern_combo.currentData())))
    pattern_row.addWidget(self.stage_pattern_combo,1)
    self.stage_change_info=stable_label("Mudanças do áudio: aguardando contexto.", "muted",2)
    pattern_row.addWidget(self.stage_change_info,2)
    layout.addLayout(pattern_row)
    row = QHBoxLayout()
    self.phrase_cells = []
    for i in range(8):
        cell = label(str(i + 1), "badge")
        cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cell.setMinimumHeight(28)
        row.addWidget(cell, 1)
        if i == 3:
            row.addSpacing(12)
        self.phrase_cells.append(cell)
    layout.addLayout(row)
    self.grid_phase_bar = QProgressBar()
    self.grid_phase_bar.setRange(0, 1000)
    self.grid_phase_bar.setTextVisible(False)
    self.grid_phase_bar.setFixedHeight(6)
    layout.addWidget(self.grid_phase_bar)
    self.stage_pattern_view=ParPatternView()
    layout.addWidget(self.stage_pattern_view)
    layout.addWidget(self.stage_view, 1)
    frame, contents = card("Estrutura e grade", "O ciclo tem oito tempos e avança pelo BPM mesmo sem kicks. Clique em Sincronizar 1/8 no início desejado.")
    self.structure_detail = stable_label("Inicie a captura para acompanhar a estrutura.", "muted", 3)
    contents.addWidget(self.structure_detail)
    self.grid_detail = stable_label("Grade: aguardando kicks regulares e BPM confiável.", "muted", 3)
    contents.addWidget(self.grid_detail)
    layout.addWidget(frame)
    row = QHBoxLayout()
    for name, target in (("Entrada de áudio →", 0), ("Ajustar efeitos e cores →", 6)):
        button = QPushButton(name)
        button.clicked.connect(lambda checked=False, index=target: self._navigate(index))
        row.addWidget(button)
    self.stage_auto_colors = QCheckBox("Cores automáticas")
    self.stage_auto_colors.setChecked(self.light_color_combo.currentData() == "automatic")
    self.stage_auto_colors.toggled.connect(lambda enabled: self.light_color_combo.setCurrentIndex(
        self.light_color_combo.findData("automatic" if enabled else "fixed")))
    row.addWidget(self.stage_music_button)
    row.addWidget(self.stage_auto_colors)
    row.addStretch()
    layout.addLayout(row)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(page)
    return scroll


def update_stage_view(self, snapshot, status, at):
    light = self.light_runtime.snapshot()
    self.stage_view.set_snapshot(light)
    self.stage_pattern_view.set_snapshot(light)
    if self.pages.currentIndex() != 7:
        return
    for button, checkbox in ((self.stage_arm_button, self.light_arm_check), (self.stage_blackout_button, self.light_blackout_button)):
        button.blockSignals(True)
        button.setChecked(checkbox.isChecked())
        button.blockSignals(False)
        button.setEnabled(not self.closing)
    self.stage_auto_colors.blockSignals(True)
    self.stage_auto_colors.setChecked(self.light_color_combo.currentData() == "automatic")
    self.stage_auto_colors.blockSignals(False)
    self.stage_auto_colors.setEnabled(not self.closing)
    self.stage_music_button.setEnabled(not self.closing)
    self.stage_show_button.setEnabled(not self.closing)
    self.stage_phrase_button.setEnabled(not self.closing)
    self.stage_sync_button.setEnabled(can_sync_phrase(self))
    selected = self.light_effect_combo.currentData() == "phrase_show"
    self.stage_show_button.blockSignals(True)
    self.stage_show_button.setChecked(selected)
    self.stage_show_button.setText("Show de 8 · LIGADO" if selected else "Show de 8 · DESLIGADO")
    self.stage_show_button.blockSignals(False)
    self.stage_pattern_combo.blockSignals(True)
    self.stage_pattern_combo.setCurrentIndex(self.stage_pattern_combo.findData(self.light_pattern_combo.currentData()))
    self.stage_pattern_combo.blockSignals(False)
    self.stage_pattern_combo.setEnabled(not self.closing)
    self.stage_change_info.setText(("TROCA NO PRÓXIMO 1/8 · " if light.phrase_pending else "Última mudança · ") +
        light.phrase_change_reason if light.phrase_change_reason else "Mantém o ritmo até uma mudança sustentada.")
    if light.mover_rhythm:
        self.stage_change_info.setText(self.stage_change_info.text()+"\nMOVs juntos · "+light.mover_rhythm)
    self.stage_change_info.setToolTip(self.stage_change_info.text())
    pattern = MOTIF_NAMES.get(light.phrase_pattern, light.phrase_pattern)
    policy = self.light_variation_combo.currentData()
    repeat = f"repetição {light.phrase_repetition}/{2 if policy == 'two_cycles' else 1}" if policy != "texture" else "mantém até novos elementos"
    fixed = self.light_pattern_combo.currentData() != "auto"
    overlay = light.status in ("breakdown", "buildup", "drop")
    text = (f"CICLO DE 8 · {pattern} · tempo {light.phrase_step}/8 · ciclo {light.phrase_cycle}"
        + "\n" + ("alinhado pelo clique" if light.phrase_synced else "grade automática")
        + " · " + ("padrão fixo" if fixed else repeat)
        + (" · troca no próximo ciclo" if light.phrase_pending else "")
        + (" · tensão/drop em destaque" if overlay else "")) if light.phrase_step else (
            "SHOW DE 8 · aguardando grade e motor ativo\nQuatro kicks regulares adquirem a grade; Sincronizar 1/8 marca o início desejado." if selected else
            "CICLOS DE 8 · ligue Show de 8\nSincronizar 1/8 também ativa o show e marca o primeiro tempo com o clique.")
    sync_at=self.light_runtime.controls().phrase_sync_at
    acknowledged=light.phrase_synced and light.phrase_sync_id==self._phrase_sync_id and sync_at is not None and 0<=at-sync_at<1.2
    if acknowledged:
        text="SINCRONIZADO · clique marcou 1/8\n"+pattern+" · "+light.show_rhythm+" · alinhado pelo clique"
    elif light.show_rhythm:
        text += " · "+light.show_rhythm
    self.stage_phrase_info.setText(text)
    self.stage_phrase_info.setToolTip(self.stage_phrase_info.text())
    self.stage_arm_button.setText("Desativar motor" if self.light_arm_check.isChecked() else "Ativar motor")
    self.stage_blackout_button.setText("LIBERAR BLACKOUT" if self.light_blackout_button.isChecked() else "BLACKOUT")
    self.stage_status.setText(STATUS_NAMES[light.status] + " · " + light.reason)
    self.stage_status.setToolTip(self.stage_status.text())
    texture = snapshot.texture if snapshot and not snapshot.texture_error else None
    texture_fresh = bool(texture and status.state == "running" and status.audio_age < 0.5 and 0 <= at - texture.updated_at < 0.6)
    for key, bar in self.texture_meters.items():
        bar.setValue(round(getattr(texture, key) * 100) if texture_fresh else 0)
    self.texture_detail.setText(f"Graves {texture.bass_db:.1f} dBFS · ataques {texture.onset_rate:.1f}/s · densidade espectral" if texture_fresh else "Áudio: aguardando descritores recentes.")
    self.texture_detail.setToolTip(self.texture_detail.text())
    structure = snapshot.structure if snapshot and not snapshot.structure_error else None
    fresh = bool(structure and status.state == "running" and status.audio_age < 0.5 and 0 <= at - structure.updated_at < 0.6)
    self.structure_metrics["state"].setText(STRUCTURE_NAMES[structure.state] if fresh else "AGUARDANDO" if status.state == "running" else "PARADO")
    self.structure_metrics["tension"].setText(f"{structure.tension:.0%}" if fresh else "—")
    self.structure_metrics["confidence"].setText(f"{structure.confidence:.0%}" if fresh else "—")
    self.structure_metrics["drop"].setText(f"{structure.drop_kicks}/8 kicks" if fresh and structure.state == "drop" else "—")
    grid = project_grid(structure.grid, at) if fresh and structure.grid else None
    phrase = (grid.beat_index - grid.phrase_origin) % 8 + 1 if grid and grid.state in ("tracking", "predicting") else 0
    light_cycle = light.effect == "phrase_show" and light.phrase_step > 0
    if light_cycle:
        phrase = light.phrase_step
    self.grid_phase_bar.setValue(round((light.phrase_phase if light_cycle else grid.phase) * 1000) if phrase else 0)
    for i, cell in enumerate(self.phrase_cells):
        active = bool(phrase and phrase == i + 1)
        if cell.property("phrase_active") == active:
            continue
        cell.setProperty("phrase_active", active)
        cell.setStyleSheet("background: #6de9c1; color: #0b211b; border-radius: 5px;" if active else "background: #1b2934; color: #7c91a1; border-radius: 5px;")
    if fresh:
        evidence = structure.drop_evidence
        power = (f"Último retorno: {evidence.power_ratio:.0%} da potência do groove · fracos bloqueados: {evidence.rejected_weak} · pausa: {'sim' if evidence.pause_recent else 'não'}"
                 if evidence and evidence.candidate_db is not None else "Potência do kick: aguardando retorno para comparar com o groove.")
        if evidence and evidence.confirmation_ms is not None:
            power += f" · última decisão: {evidence.confirmation_ms:.0f} ms de análise"
            if evidence.rescued_attack:
                power += " · ataque recuperado"
        if evidence and evidence.reference_peak_db is not None:
            power += f" · média de {evidence.reference_kicks} kicks: {evidence.reference_peak_db:.1f} dB · pico relativo: {evidence.peak_ratio:.0%}"
            if evidence.mean_reached:
                power += " · força do groove atingida"
        self.structure_detail.setText(structure.reason + f" · retornos bloqueados: {structure.rejected_returns}\n" + power +
            f"\nAtaques: {structure.onset_rate:.1f}/s · roll: {structure.roll_rate:.1f}/s · sem kick forte há {structure.kick_gap:.1f} s · movimento: {light.movement_hz:.2f} ciclos/s · W: {max(s.white for s in light.states):.0%}")
    elif snapshot and snapshot.structure_error:
        self.structure_detail.setText("Análise estrutural indisponível: " + snapshot.structure_error)
    else:
        self.structure_detail.setText("Inicie a captura; a grade se adquire com quatro kicks regulares na faixa de BPM. Ligue ‘Show de 8’ para repetir e variar os padrões.")
    self.structure_detail.setToolTip(self.structure_detail.text())
    if grid and grid.state in ("tracking", "predicting"):
        wait = max(0.0, grid.next_kick_at - at)
        phrase_wait = max(0.0, grid.next_phrase_at - at)
        future = f"em {max(0, grid.forecast_30_at - at):.2f} s" if grid.forecast_30_at else "sem confiança suficiente"
        self.grid_detail.setText(f"Grade {'prevista' if grid.state == 'predicting' else 'acompanhada'} · próximo tempo em {wait:.2f} s · frase relativa em {phrase_wait:.2f} s · confiança {grid.confidence:.0%}\n"
            f"Janela na grade +30 s: {future} · incerteza atual ±{grid.uncertainty_ms:.0f} ms · rejeições grade/perfil: {grid.rejected_offgrid}/{structure.rejected_timbre}\n"
            f"Correções: {grid.corrections} · último desvio: {grid.last_correction_ms:+.0f} ms · cores: {light.color_profile}")
    else:
        self.grid_detail.setText("Grade: reaprendendo a referência." if grid and grid.state == "expired" else "Grade: aguardando kicks regulares e BPM confiável.")
    self.grid_detail.setToolTip(self.grid_detail.text())
