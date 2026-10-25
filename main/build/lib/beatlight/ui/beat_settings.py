from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout
from beatlight.ui.components import card, label


def build_beat_settings(self):
    frame, layout = card("BPM e sincronização", "Faixa preferida do andamento e duração máxima da previsão sem kicks alinhados.")
    form = QFormLayout()
    form.setSpacing(12)
    self.beat_spins = {}
    for key, title, low, high, suffix in (
        ("beat_min_bpm", "BPM mínimo", 40, 230, " BPM"),
        ("beat_max_bpm", "BPM máximo", 50, 240, " BPM"),
        ("beat_hold_seconds", "Manter estimativa sem referência", 1, 12, " s")):
        spin = QDoubleSpinBox()
        spin.setRange(low, high)
        spin.setDecimals(1)
        spin.setSingleStep(0.5 if key == "beat_hold_seconds" else 1)
        spin.setSuffix(suffix)
        self.beat_spins[key] = spin
        form.addRow(title, spin)
    layout.addLayout(form)
    layout.addWidget(label("A faixa de BPM orienta a escolha entre metade e dobro. Durante pausas curtas, o relógio segue como estimado, com confiança decrescente. Salve e reinicie a captura para aplicar.", "muted", True))
    self.beat_widgets = tuple(self.beat_spins.values())
    load_beat_settings(self, self.settings)
    return frame


def load_beat_settings(self, settings):
    for key, spin in self.beat_spins.items():
        spin.setValue(getattr(settings, key))


def beat_form_values(self):
    return {key: spin.value() for key, spin in self.beat_spins.items()}
