"""Inspeção de estados abstratos e comandos operacionais; não gera efeitos."""
from time import monotonic
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox,
    QFormLayout, QHBoxLayout, QHeaderView, QProgressBar, QPushButton, QScrollArea,
    QTableWidget, QTableWidgetItem, QSizePolicy, QVBoxLayout, QWidget)
from beatlight.lighting.config import LightConfig, LightingControls
from beatlight.lighting.rgbw import preview_rgb
from beatlight.music.grid import project_grid
from beatlight.lighting.phrase import MOTIF_NAMES, MOTIFS
from beatlight.lighting.movers import MOVER_STYLES
from beatlight.lighting.breakdown import BREAKDOWN_STYLES
from beatlight.ui.components import card, label, metric, stable_label

EFFECT_NAMES = {"phrase_show": "Show cíclico · 8 tempos", "orchestrated_show": "Show RGBW · cenas em camadas", "rhythmic_show": "Show rítmico · padrões, baixo e camadas", "kick_pulse": "Pulso por kick", "beat_pulse": "Pulso pelo relógio", "beat_chase": "Alternância A/B por batida", "ambient": "Movimento ambiente", "musical": "Automação musical · baixo, densidade e kicks", "bass_flow": "Linha de baixo · envelope dos graves", "density_wash": "Densidade sonora · distribuição dos fachos"}
PERCENT_FIELDS = ("light_master", "light_movement_speed", "light_kick_weight", "light_bass_weight", "light_density_weight", "light_white_strength", "light_show_complexity", "light_change_sensitivity")
STATUS_NAMES = {"disabled": "DESATIVADO", "blackout": "BLACKOUT", "manual": "MANUAL", "active": "AUTOMÁTICO", "estimated": "ESTIMADO", "ambient": "AMBIENTE", "waiting": "AGUARDANDO", "error": "FALHA", "stopped": "ENCERRADO", "breakdown": "BREAKDOWN", "buildup": "BUILD-UP", "drop": "DROP"}


def build_lighting_page(self):
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(14)
    toolbar = QHBoxLayout()
    self.light_source = stable_label("Motor abstrato · nenhuma saída física conectada", "subtitle", 2)
    toolbar.addWidget(self.light_source, 1)
    stage = QPushButton("Ver palco →")
    stage.clicked.connect(lambda: self._navigate(7))
    toolbar.addWidget(stage)
    audio = QPushButton("Entrada de áudio →")
    audio.clicked.connect(lambda: self._navigate(0))
    toolbar.addWidget(audio)
    self.light_arm_check = QCheckBox("Ativar motor")
    toolbar.addWidget(self.light_arm_check)
    self.light_blackout_button = QPushButton("BLACKOUT")
    self.light_blackout_button.setObjectName("stop")
    self.light_blackout_button.setCheckable(True)
    toolbar.addWidget(self.light_blackout_button)
    layout.addLayout(toolbar)
    row = QHBoxLayout()
    self.light_metrics = {}
    for key, title, note in (("status", "ESTADO DO MOTOR", "Blackout > manual > automação"),
        ("fixtures", "LUMINÁRIAS ABSTRATAS", "4 PARs + 2 moving heads RGBW"),
        ("rate", "ATUALIZAÇÃO DO MOTOR", "Worker independente da GUI"),
        ("time", "TEMPO DE PROCESSAMENTO", "Último quadro de iluminação")):
        frame, value = metric(title, note)
        value.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        value.setFixedHeight(value.fontMetrics().lineSpacing() + 6)
        self.light_metrics[key] = value
        row.addWidget(frame)
    layout.addLayout(row)
    row = QHBoxLayout()
    frame, contents = card("Efeito e intensidade", "Os ajustes de luz são aplicados em tempo real.")
    form = QFormLayout()
    form.setSpacing(10)
    self._phrase_sync_id, self._phrase_sync_at = 0, None
    self.light_pattern_combo = QComboBox()
    self.light_pattern_combo.addItem("Automático · variar os padrões", "auto")
    for key in MOTIFS:
        self.light_pattern_combo.addItem(MOTIF_NAMES[key], key)
    self.light_variation_combo = QComboBox()
    for key, name in (("texture", "Mudar somente com novos elementos"), ("two_cycles", "Repetir 2 ciclos de 8 e mudar"), ("cycle", "Mudar a cada ciclo de 8")):
        self.light_variation_combo.addItem(name, key)
    self.light_mover_combo = QComboBox()
    self.light_mover_combo.addItem("Automático · acompanha o contexto","auto")
    for key,name in MOVER_STYLES.items():
        self.light_mover_combo.addItem(name,key)
    self.light_breakdown_combo = QComboBox()
    self.light_breakdown_combo.addItem("Automático · estilos suaves","auto")
    for key,name in BREAKDOWN_STYLES.items():
        self.light_breakdown_combo.addItem(name,key)
    self.light_prepare_combo = QComboBox()
    for key,name in (("fade","Fade-out rápido"),("blackout","Apagão breve"),("none","Sem preparação")):
        self.light_prepare_combo.addItem(name,key)
    self.light_effect_combo = QComboBox()
    for key, name in EFFECT_NAMES.items():
        self.light_effect_combo.addItem(name, key)
    self.light_color_combo = QComboBox()
    self.light_color_combo.addItem("Automático · acompanha o áudio", "automatic")
    self.light_color_combo.addItem("Fixo · usar a paleta escolhida", "fixed")
    self.light_palette_combo = QComboBox()
    for key, name in (("mint_blue", "Menta / Azul"), ("amber_violet", "Âmbar / Violeta"), ("red_blue", "Vermelho / Azul"), ("cyan_magenta", "Ciano / Magenta"), ("lime_rose", "Lima / Rosa"), ("gold_ice", "Ouro / Gelo"), ("white", "Branco · canal W")):
        self.light_palette_combo.addItem(name, key)
    self.light_spins = {}
    for key, low, high, suffix, step, decimals in (
        ("light_master", 0, 100, "%", 5, 0), ("light_pulse_ms", 80, 1000, " ms", 20, 0),
        ("light_transition_ms", 0, 3000, " ms", 100, 0), ("light_movement_speed", 0, 100, "%", 5, 0),
        ("light_kick_weight", 0, 100, "%", 5, 0), ("light_bass_weight", 0, 100, "%", 5, 0),
        ("light_density_weight", 0, 100, "%", 5, 0),
        ("light_white_strength", 0, 100, "%", 5, 0), ("light_show_complexity", 0, 100, "%", 5, 0),
        ("light_change_sensitivity", 50, 200, "%", 10, 0),
        ("light_phrase_prepare_ms", 40, 300, " ms", 10, 0)):
        spin = QDoubleSpinBox()
        spin.setRange(low, high)
        spin.setSuffix(suffix)
        spin.setSingleStep(step)
        spin.setDecimals(decimals)
        self.light_spins[key] = spin
    form.addRow("Efeito", self.light_effect_combo)
    form.addRow("Perfil de cores", self.light_color_combo)
    form.addRow("Paleta fixa / manual", self.light_palette_combo)
    form.addRow("Intensidade geral", self.light_spins["light_master"])
    form.addRow("Duração do pulso", self.light_spins["light_pulse_ms"])
    form.addRow("Transição entre modos/cores", self.light_spins["light_transition_ms"])
    form.addRow("Movimento · limite no modo musical", self.light_spins["light_movement_speed"])
    form.addRow("Peso dos kicks confirmados", self.light_spins["light_kick_weight"])
    form.addRow("Peso da linha de baixo", self.light_spins["light_bass_weight"])
    form.addRow("Peso da densidade sonora", self.light_spins["light_density_weight"])
    form.addRow("Uso do canal W · paletas/automático", self.light_spins["light_white_strength"])
    form.addRow("Variedade do show", self.light_spins["light_show_complexity"])
    form.addRow("Sensibilidade às mudanças do áudio", self.light_spins["light_change_sensitivity"])
    form.addRow("Padrão do ciclo de oito", self.light_pattern_combo)
    form.addRow("Ritmo dos moves · sempre juntos",self.light_mover_combo)
    form.addRow("Breakdown calmo",self.light_breakdown_combo)
    form.addRow("Variação automática", self.light_variation_combo)
    form.addRow("Antes de cada ciclo", self.light_prepare_combo)
    form.addRow("Duração da preparação", self.light_spins["light_phrase_prepare_ms"])
    contents.addLayout(form)
    self.light_sync_button = QPushButton("Sincronizar primeiro tempo · 1/8")
    self.light_sync_button.clicked.connect(lambda: sync_phrase(self))
    contents.addWidget(self.light_sync_button)
    contents.addWidget(label("No Show rítmico, os PARs alternam padrões de oito tempos; novas camadas provocam viradas. Tensão e energia controlam velocidade, cor e brilho. O ajuste de movimento limita a velocidade; zero congela a posição.", "muted", True))
    row.addWidget(frame, 1)
    frame, contents = card("Controle manual", "Substitui o efeito automático; master e blackout continuam valendo.")
    self.light_manual_check = QCheckBox("Assumir controle manual")
    self.light_rgbw_check = QCheckBox("Escolher canais R/G/B/W manualmente")
    for checkbox in (self.light_arm_check, self.light_manual_check, self.light_rgbw_check):
        checkbox.setStyleSheet("QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #536a78; border-radius: 3px; background: #11181d; } QCheckBox::indicator:checked { background: #6de9c1; border-color: #6de9c1; }")
    contents.addWidget(self.light_manual_check)
    contents.addWidget(self.light_rgbw_check)
    form = QFormLayout()
    self.light_manual_spins = {}
    for key, name, value in (("manual_intensity", "Intensidade manual", 70), ("manual_pan", "Pan dos moving heads", 50), ("manual_tilt", "Tilt dos moving heads", 50),
        ("manual_red", "R · vermelho", 25), ("manual_green", "G · verde", 100),
        ("manual_blue", "B · azul", 70), ("manual_white", "W · branco", 0)):
        spin = QDoubleSpinBox()
        spin.setRange(0, 100)
        spin.setDecimals(0)
        spin.setSuffix("%")
        spin.setValue(value)
        self.light_manual_spins[key] = spin
        form.addRow(name, spin)
    contents.addLayout(form)
    contents.addWidget(label("Pan e tilt são posições normalizadas. O inventário atual é de demonstração e não possui endereços DMX.", "muted", True))
    contents.addStretch()
    save = QPushButton("Salvar preferências de luz")
    save.clicked.connect(self._save_lighting_settings)
    contents.addWidget(save)
    row.addWidget(frame, 1)
    layout.addLayout(row)
    frame, contents = card("Estados produzidos pelo motor", "Inspeção numérica · acompanhe os fachos e movimentos em Stage Preview")
    self.light_table = QTableWidget(len(self.light_runtime.engine.fixtures), 7)
    self.light_table.setHorizontalHeaderLabels(("Luminária", "Grupos", "Intensidade", "Cor aparente", "Pan", "Tilt", "Canal W"))
    self.light_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    self.light_table.verticalHeader().hide()
    self.light_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    self.light_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    self.light_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    self.light_table.setFixedHeight(230)
    self.light_table.setStyleSheet("QTableWidget { background: #11181d; color: #dce5e9; border: 0; gridline-color: #25313a; } QHeaderView::section { background: #1b252c; color: #a4b6c3; border: 0; padding: 6px; }")
    self.light_rows = {}
    for row_index, fixture in enumerate(self.light_runtime.engine.fixtures):
        bar = QProgressBar()
        bar.setRange(0, 1000)
        bar.setValue(0)
        self.light_table.setCellWidget(row_index, 2, bar)
        for column in (0, 1, 3, 4, 5, 6):
            item = QTableWidgetItem()
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.light_table.setItem(row_index, column, item)
        self.light_table.item(row_index, 0).setText(fixture.name)
        self.light_table.item(row_index, 0).setToolTip(" / ".join(fixture.capabilities))
        self.light_table.item(row_index, 1).setText(" / ".join(fixture.groups))
        self.light_rows[fixture.fixture_id] = (row_index, fixture, bar)
    contents.addWidget(self.light_table)
    self.light_detail = stable_label("Motor desativado.", "muted", 3)
    contents.addWidget(self.light_detail)
    layout.addWidget(frame)
    self._light_last_error = ""
    self.light_notice = label("Ative o motor para testar. Efeitos musicais usam a captura; ambiente e manual podem funcionar sem áudio. Blackout zera intensidades e permanece ativo até ser liberado.", "notice", True)
    layout.addWidget(self.light_notice)
    export = QPushButton("Exportar estados JSON")
    export.clicked.connect(self._export_lighting_states)
    layout.addWidget(export, 0, Qt.AlignmentFlag.AlignRight)
    self.light_config_widgets = (self.light_effect_combo, self.light_palette_combo, self.light_color_combo, self.light_pattern_combo, self.light_variation_combo, self.light_mover_combo, self.light_breakdown_combo, self.light_prepare_combo, *self.light_spins.values())
    self.light_widgets = (*self.light_config_widgets, self.light_arm_check, self.light_blackout_button,
                          self.light_sync_button, self.light_manual_check, self.light_rgbw_check, *self.light_manual_spins.values(), save, export)
    load_lighting_settings(self, self.settings)
    for widget in (self.light_arm_check, self.light_blackout_button, self.light_manual_check, self.light_rgbw_check):
        widget.toggled.connect(self._lighting_changed)
    for widget in (self.light_effect_combo, self.light_palette_combo, self.light_color_combo, self.light_pattern_combo, self.light_variation_combo, self.light_mover_combo, self.light_breakdown_combo, self.light_prepare_combo):
        widget.currentIndexChanged.connect(self._lighting_changed)
    for spin in (*self.light_spins.values(), *self.light_manual_spins.values()):
        spin.valueChanged.connect(self._lighting_changed)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(page)
    return scroll


def lighting_form_values(self):
    values = {key: spin.value() / (100 if key in PERCENT_FIELDS else 1) for key, spin in self.light_spins.items()}
    return dict(light_effect=self.light_effect_combo.currentData(), light_palette=self.light_palette_combo.currentData(), light_color_mode=self.light_color_combo.currentData(), light_phrase_pattern=self.light_pattern_combo.currentData(),
        light_phrase_prepare=self.light_prepare_combo.currentData(), light_phrase_variation=self.light_variation_combo.currentData(), light_mover_pattern=self.light_mover_combo.currentData(),
        light_breakdown_style=self.light_breakdown_combo.currentData(), **values)


def apply_lighting_controls(self):
    self.light_runtime.set_controls(LightingControls(
        LightConfig(**lighting_form_values(self)), self.light_arm_check.isChecked(),
        self.light_blackout_button.isChecked(), self.light_manual_check.isChecked(),
        manual_rgbw=self.light_rgbw_check.isChecked(), phrase_sync_id=self._phrase_sync_id, phrase_sync_at=self._phrase_sync_at,
        **{key: spin.value() / 100 for key, spin in self.light_manual_spins.items()}))


def load_lighting_settings(self, settings):
    for widget in self.light_config_widgets:
        widget.blockSignals(True)
    self.light_effect_combo.setCurrentIndex(self.light_effect_combo.findData(settings.light_effect))
    self.light_palette_combo.setCurrentIndex(self.light_palette_combo.findData(settings.light_palette))
    self.light_color_combo.setCurrentIndex(self.light_color_combo.findData(settings.light_color_mode))
    self.light_pattern_combo.setCurrentIndex(self.light_pattern_combo.findData(settings.light_phrase_pattern))
    self.light_variation_combo.setCurrentIndex(self.light_variation_combo.findData(settings.light_phrase_variation))
    self.light_mover_combo.setCurrentIndex(self.light_mover_combo.findData(settings.light_mover_pattern))
    self.light_breakdown_combo.setCurrentIndex(self.light_breakdown_combo.findData(settings.light_breakdown_style))
    self.light_prepare_combo.setCurrentIndex(self.light_prepare_combo.findData(settings.light_phrase_prepare))
    for key, spin in self.light_spins.items():
        spin.setValue(getattr(settings, key) * (100 if key in PERCENT_FIELDS else 1))
    for widget in self.light_config_widgets:
        widget.blockSignals(False)
    apply_lighting_controls(self)


def update_lighting_view(self):
    snapshot = self.light_runtime.snapshot()
    for widget in self.light_widgets:
        widget.setEnabled(not self.closing)
    self.light_sync_button.setEnabled(can_sync_phrase(self))
    self.light_rgbw_check.setEnabled(self.light_manual_check.isChecked() and not self.closing)
    for key, spin in self.light_manual_spins.items():
        channel = key in ("manual_red", "manual_green", "manual_blue", "manual_white")
        spin.setEnabled(self.light_manual_check.isChecked() and not self.closing
            and (not channel or self.light_rgbw_check.isChecked()))
    self.light_palette_combo.setEnabled(not self.closing and (self.light_color_combo.currentData() == "fixed" or self.light_manual_check.isChecked()))
    self.light_metrics["status"].setText(STATUS_NAMES[snapshot.status])
    self.light_metrics["fixtures"].setText(f"{len(snapshot.states):02d}")
    self.light_metrics["rate"].setText(f"{snapshot.update_hz:.1f} Hz" if snapshot.update_hz else "—")
    self.light_metrics["time"].setText(f"{snapshot.processing_ms:.2f} ms")
    self.light_blackout_button.setText("LIBERAR BLACKOUT" if self.light_blackout_button.isChecked() else "BLACKOUT")
    source = "TESTE SINTÉTICO" if self.source_combo.currentData() in ("synthetic", "structure_demo", "texture_demo") else "WASAPI LOOPBACK"
    self.light_source.setText(source + " · ESTADOS ABSTRATOS · SEM SAÍDA FÍSICA")
    self.light_detail.setText(snapshot.reason + f"\nQuadro {snapshot.frame_id} · master {snapshot.master:.0%} · referência musical {snapshot.beat_state}\nCores: {snapshot.color_profile}")
    if snapshot.error:
        if snapshot.error != self._light_last_error:
            self._event("Falha no motor de iluminação: " + snapshot.error)
        self.light_notice.setText("Falha de iluminação: " + snapshot.error + ". Estados zerados; altere um controle para tentar novamente.")
    elif self._light_last_error:
        self.light_notice.setText("Motor recuperado. Estados abstratos disponíveis para inspeção.")
    self._light_last_error = snapshot.error
    if self.pages.currentIndex() != 6:
        return
    for state in snapshot.states:
        row, fixture, bar = self.light_rows[state.fixture_id]
        bar.setValue(round(state.intensity * 1000))
        color = QColor.fromRgbF(*preview_rgb(state))
        item = self.light_table.item(row, 3)
        item.setText(color.name().upper())
        item.setBackground(color)
        item.setForeground(QColor("#10171b") if color.lightnessF() > 0.5 else QColor("#ffffff"))
        item.setToolTip("RGBW normalizado: " + ", ".join(f"{v:.3f}" for v in (*state.color, state.white)))
        self.light_table.item(row, 6).setText(f"{state.white:.0%}" if "white" in fixture.capabilities else "—")
        self.light_table.item(row, 4).setText(f"{state.pan:.0%}" if "pan" in fixture.capabilities else "—")
        self.light_table.item(row, 5).setText(f"{state.tilt:.0%}" if "tilt" in fixture.capabilities else "—")


def can_sync_phrase(self):
    status = self.runtime.status()
    snapshot = self._effective_snapshot() if hasattr(self, "_effective_snapshot") else self.runtime.snapshot()
    structure = snapshot.structure if snapshot and not snapshot.structure_error else None
    at = monotonic()
    controls = self.light_runtime.controls()
    grid = project_grid(structure.grid, at) if structure and structure.grid else None
    return bool(not self.closing and status.state == "running" and status.audio_age < .5
        and structure and 0 <= at-structure.updated_at < .6 and structure.state != "silence"
        and grid and grid.state in ("tracking", "predicting") and grid.period and grid.confidence >= .35
        and controls.armed and not controls.manual and not controls.blackout)


def sync_phrase(self):
    if not can_sync_phrase(self):
        return
    self._phrase_sync_id += 1
    self._phrase_sync_at = monotonic()
    self.light_effect_combo.blockSignals(True)
    self.light_effect_combo.setCurrentIndex(self.light_effect_combo.findData("phrase_show"))
    self.light_effect_combo.blockSignals(False)
    apply_lighting_controls(self)
    self._event("Ciclo visual alinhado: o clique marcou o primeiro tempo de oito.")
