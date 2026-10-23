"""Ajustes explícitos do detector; aplicados somente na próxima captura."""
from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout
from beatlight.ui.components import card, label
from beatlight.dsp.kick_config import KickConfig


def build_kick_settings(self):
    frame, layout = card("Detecção de kicks", "O detector usa a entrada original e uma análise própria, independente dos filtros do espectro.")
    form = QFormLayout()
    form.setSpacing(12)
    self.kick_spins = {}
    for key, title, low, high, step, suffix, decimals in (
        ("kick_low_hz", "Corte inferior", 20, 375, 5, " Hz", 1),
        ("kick_high_hz", "Corte superior", 45, 400, 5, " Hz", 1),
        ("kick_sensitivity", "Sensibilidade", 0.5, 2, 0.1, " ×", 2),
        ("kick_refractory_ms", "Intervalo mínimo entre kicks", 100, 400, 10, " ms", 0),
        ("kick_floor_db", "Piso da energia na banda", -90, -30, 3, " dBFS", 1)):
        spin = QDoubleSpinBox()
        spin.setRange(low, high)
        spin.setSingleStep(step)
        spin.setDecimals(decimals)
        spin.setSuffix(suffix)
        self.kick_spins[key] = spin
        form.addRow(title, spin)
    layout.addLayout(form)
    layout.addWidget(label("Aumente a sensibilidade se perder kicks; reduza se houver disparos extras. O intervalo mínimo limita repiques. Salve e reinicie a captura para comparar.", "muted", True))
    self.kick_widgets = tuple(self.kick_spins.values())
    load_kick_settings(self, self.settings)
    return frame


def load_kick_settings(self, settings):
    for key in KickConfig.__dataclass_fields__:
        self.kick_spins[key].setValue(getattr(settings, key))


def kick_form_values(self):
    return {key: spin.value() for key, spin in self.kick_spins.items()}
