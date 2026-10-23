"""Formulário de parâmetros DSP; validação pertence aos modelos de configuração."""
from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout
from beatlight.ui.components import card, label


def build_dsp_settings(self):
    frame, layout = card("Análise espectral e filtros", "Salve os ajustes com a captura parada antes de iniciar outra sessão.")
    form = QFormLayout()
    form.setSpacing(12)
    self.fft_combo = QComboBox()
    for size in (1024, 2048, 4096, 8192):
        self.fft_combo.addItem(f"{size} amostras", size)
    self.overlap_combo = QComboBox()
    for value in (25, 50, 75):
        self.overlap_combo.addItem(f"{value}%", value)
    self.dc_check = QCheckBox("Remover DC da análise (passa-alta 20 Hz)")
    self.filter_combo = QComboBox()
    for title, mode in (("Desativado", "none"), ("Passa-baixa", "lowpass"), ("Passa-alta", "highpass"), ("Passa-banda", "bandpass")):
        self.filter_combo.addItem(title, mode)
    def frequency():
        spin = QDoubleSpinBox()
        spin.setRange(1, 20000)
        spin.setDecimals(1)
        spin.setSuffix(" Hz")
        return spin
    self.filter_low_spin, self.filter_high_spin = frequency(), frequency()
    self.low_mid_spin, self.mid_high_spin = frequency(), frequency()
    form.addRow("Tamanho da FFT", self.fft_combo)
    form.addRow("Sobreposição das janelas", self.overlap_combo)
    form.addRow("Pré-processamento", self.dc_check)
    form.addRow("Pré-filtro de análise", self.filter_combo)
    form.addRow("Corte inferior / passa-alta", self.filter_low_spin)
    form.addRow("Corte superior / passa-baixa", self.filter_high_spin)
    form.addRow("Divisão graves / médios", self.low_mid_spin)
    form.addRow("Divisão médios / agudos", self.mid_high_spin)
    layout.addLayout(form)
    layout.addWidget(label("Uma FFT maior melhora a resolução em frequência e aumenta o tempo necessário para preencher a janela. Os medidores da entrada usam o áudio original.", "muted", True))
    self.dsp_widgets = (self.fft_combo, self.overlap_combo, self.dc_check, self.filter_combo,
                        self.filter_low_spin, self.filter_high_spin, self.low_mid_spin, self.mid_high_spin)
    load_dsp_settings(self, self.settings)
    return frame


def load_dsp_settings(self, settings):
    self.fft_combo.setCurrentIndex(self.fft_combo.findData(settings.fft_size))
    self.overlap_combo.setCurrentIndex(self.overlap_combo.findData(settings.fft_overlap))
    self.dc_check.setChecked(settings.remove_dc)
    self.filter_combo.setCurrentIndex(self.filter_combo.findData(settings.filter_mode))
    self.filter_low_spin.setValue(settings.filter_low_hz)
    self.filter_high_spin.setValue(settings.filter_high_hz)
    self.low_mid_spin.setValue(settings.low_mid_hz)
    self.mid_high_spin.setValue(settings.mid_high_hz)


def dsp_form_values(self) -> dict:
    return dict(fft_size=self.fft_combo.currentData(), fft_overlap=self.overlap_combo.currentData(),
                remove_dc=self.dc_check.isChecked(), filter_mode=self.filter_combo.currentData(),
                filter_low_hz=self.filter_low_spin.value(), filter_high_hz=self.filter_high_spin.value(),
                low_mid_hz=self.low_mid_spin.value(), mid_high_hz=self.mid_high_spin.value())
