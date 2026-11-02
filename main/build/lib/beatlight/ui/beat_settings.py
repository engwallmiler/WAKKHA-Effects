from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QFormLayout
from beatlight.ui.components import card, label


def build_beat_settings(self):
    frame, layout = card("BPM e sincronização", "Escolha como a grade por áudio adquire e mantém o andamento.")
    form = QFormLayout()
    form.setSpacing(12)
    self.beat_spins = {}
    self.beat_mode_combo = QComboBox()
    for text, value in (
        ('Automático · BPM inteiro estável', 'integer'),
        ('BPM fixo informado', 'manual'),
        ('Contínuo · permite frações', 'continuous'),
    ):
        self.beat_mode_combo.addItem(text, value)
    form.addRow('Modo da grade', self.beat_mode_combo)
    for key, title, low, high, suffix in (
        ("beat_min_bpm", "BPM mínimo", 40, 230, " BPM"),
        ("beat_max_bpm", "BPM máximo", 50, 240, " BPM"),
        ("beat_hold_seconds", "Diagnóstico acústico · previsão sem referência", 1, 12, " s"),
        ("beat_fixed_bpm", "BPM fixo · usado no modo informado", 40, 240, " BPM")):
        spin = QDoubleSpinBox()
        spin.setRange(low, high)
        spin.setDecimals(0 if key == 'beat_fixed_bpm' else 1)
        spin.setSingleStep(0.5 if key == "beat_hold_seconds" else 1)
        spin.setSuffix(suffix)
        self.beat_spins[key] = spin
        form.addRow(title, spin)
    layout.addLayout(form)
    layout.addWidget(label("A faixa de BPM orienta a aquisição automática e a escolha entre metade e dobro. A grade aprendida segue em trechos sem kick enquanto houver contexto de áudio. O prazo acima limita o diagnóstico acústico.", "muted", True))
    layout.addWidget(label('Inteiro estável mantém o período e exige mudança consistente para trocar. BPM fixo usa exatamente o valor informado. A grade sozinha não cria kicks. Pare a captura, salve e reinicie para aplicar.', 'muted', True))
    self.beat_widgets = (*self.beat_spins.values(), self.beat_mode_combo)
    load_beat_settings(self, self.settings)
    return frame


def load_beat_settings(self, settings):
    self.beat_mode_combo.setCurrentIndex(self.beat_mode_combo.findData(settings.beat_grid_mode))
    for key, spin in self.beat_spins.items():
        spin.setValue(getattr(settings, key))


def beat_form_values(self):
    return {**{key: spin.value() for key, spin in self.beat_spins.items()},
        'beat_grid_mode': self.beat_mode_combo.currentData()}
