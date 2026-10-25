"""Painel separado de sincronização externa. Não controla decks nem transporte."""
from time import monotonic
from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QHBoxLayout, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget
from beatlight.ui.components import card, label, metric
from beatlight.sync.timeline import link_grid


def build_link_page(self):
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)
    panel, contents = card("Ableton Link · Traktor", "BPM e fase compartilhados na rede local. A análise de estrutura continua recebendo o áudio pelo WASAPI.")
    row = QHBoxLayout()
    self.link_enable = QPushButton("Ativar Ableton Link")
    self.link_enable.setObjectName("primary")
    self.link_enable.setStyleSheet("QPushButton { background: #69e5bc; color: #0b2a20; } QPushButton:hover { background: #9af5d6; } QPushButton:disabled { background: #2b4b40; color: #698e80; }")
    self.link_enable.setCheckable(True)
    self.link_enable.toggled.connect(self._toggle_link)
    row.addWidget(self.link_enable)
    self.link_badge = label("DESATIVADO", "badge")
    row.addWidget(self.link_badge)
    row.addStretch()
    contents.addLayout(row)
    self.link_use = QCheckBox("Usar Link como relógio da grade e dos efeitos (retorno ao áudio se perder conexão)")
    self.link_use.setStyleSheet("QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #778693; border-radius: 3px; background: #11171b; } QCheckBox::indicator:checked { background: #69e5bc; border-color: #69e5bc; }")
    self.link_use.setChecked(self.settings.sync_source == "link")
    self.link_use.toggled.connect(self._link_options_changed)
    contents.addWidget(self.link_use)
    row = QHBoxLayout()
    row.addWidget(label("Compensação visual", "eyebrow"))
    self.link_offset = QDoubleSpinBox()
    self.link_offset.setRange(-250, 250)
    self.link_offset.setDecimals(0)
    self.link_offset.setSuffix(" ms")
    self.link_offset.setValue(self.settings.link_offset_ms)
    self.link_offset.valueChanged.connect(self._link_options_changed)
    row.addWidget(self.link_offset)
    row.addWidget(label("Positivo atrasa as luzes; negativo adianta. Comece com 0 ms.", "muted", True), 1)
    contents.addLayout(row)
    self.link_notice = label("Ative o LINK no Traktor primeiro. A conexão é ativada manualmente a cada abertura do BEATLIGHT.", "notice", True)
    contents.addWidget(self.link_notice)
    layout.addWidget(panel)
    row = QHBoxLayout()
    self.link_metrics = {}
    for key, title, note in (("peers", "PARTICIPANTES", "Outros aplicativos Link na sessão"),
        ("bpm", "BPM LINK", "Tempo compartilhado; não identifica o deck"),
        ("phase", "CICLO DE 8 TEMPOS", "Referência Link; início da frase é ajustável"),
        ("source", "RELÓGIO DOS EFEITOS", "Link disponível ou análise de áudio")):
        frame, value = metric(title, note)
        self.link_metrics[key] = value
        frame.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        frame.layout().itemAt(0).widget().setWordWrap(True)
        frame.layout().itemAt(2).widget().setWordWrap(True)
        row.addWidget(frame, 1)
    layout.addLayout(row)
    panel, contents = card("Configurar no Traktor", "A grade da track deve estar correta antes de sincronizar.")
    contents.addWidget(label(
        "1. Em Preferences → External Sync → External Clock Source, selecione LINK. Em versões anteriores, exiba a Global Section.\n"
        "2. Ative LINK na seção Master Clock do Traktor. Use BeatSync em Preferences → Transport → Sync Mode.\n"
        "3. Ative SYNC no deck e reproduza a track. Confira se o beatgrid acompanha os kicks.\n"
        "4. Aqui, clique Ativar Ableton Link e marque Usar Link como relógio. Aguarde ao menos 1 participante.\n"
        "5. Inicie a captura da saída do Traktor em Audio Monitor e ative os efeitos em Lighting Studio ou Stage Preview.\n"
        "6. No início desejado de um grupo de oito tempos, use Sincronizar 1/8. Esse botão alinha somente o ciclo visual.",
        "subtitle", True))
    layout.addWidget(panel)
    panel, contents = card("O que o Link informa", "O relógio continua avançando mesmo com os decks parados.")
    contents.addWidget(label("Link transmite tempo e fase. Não transmite áudio, nome da música, posição da track ou estrutura musical. Participantes não identificam o Traktor pelo nome. O áudio continua necessário para kicks, tensão, drops e iluminação automática. Não é preciso instalar Ableton Live.", "muted", True))
    contents.addWidget(label("Se não encontrar participantes: use a mesma rede local (ou o mesmo computador), confira LINK nos dois apps e a permissão do executável Python no Firewall para a rede privada. Prefira cabo; VPN e isolamento de clientes Wi-Fi podem impedir descoberta. Consulte docs/ableton-link.md para detalhes.", "muted", True))
    layout.addWidget(panel)
    layout.addStretch()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(page)
    return scroll


def update_link_view(self):
    state = self.link_runtime.snapshot()
    connected = state.usable(monotonic())
    grid = link_grid(state, monotonic(), self._sync_options[1]) if connected else None
    names = {"disabled": "DESATIVADO", "starting": "INICIANDO", "waiting": "SEM PARTICIPANTES", "connected": "CONECTADO", "error": "ERRO"}
    self.link_badge.setText(names[state.state] if state.state != "connected" or connected else "SEM ATUALIZAÇÃO")
    self.link_enable.blockSignals(True)
    self.link_enable.setChecked(state.state in ("starting", "waiting", "connected"))
    self.link_enable.setText("Desativar Ableton Link" if self.link_enable.isChecked() else "Ativar Ableton Link")
    self.link_enable.blockSignals(False)
    self.link_enable.setEnabled(not self.busy and not self.closing and self.link_runtime.available())
    self.link_metrics["peers"].setText(str(state.peers))
    self.link_metrics["bpm"].setText(f"{state.tempo:.2f}" if connected else "—")
    self.link_metrics["phase"].setText(f"{grid.beat_index % 8 + 1}/8 · {grid.phase:.0%}" if grid else "—")
    self.link_metrics["source"].setText("LINK" if connected and self._sync_options[0] == "link" else "ÁUDIO")
    if not self.link_runtime.available():
        text = "Módulo opcional ausente. Feche o BEATLIGHT e execute instalar-link.cmd; depois abra novamente."
    elif state.error:
        text = "Falha no módulo Link: " + state.error + ". A sincronização por áudio continua disponível."
    elif connected:
        text = "Link conectado. " + ("Grade e efeitos seguem o Link; estrutura e kicks continuam acústicos." if self._sync_options[0] == "link" else "Monitorando Link; grade e efeitos continuam no relógio por áudio.")
    elif state.state == "waiting":
        text = "Link ativado, mas sem outros participantes. Ative LINK no Traktor; usando o áudio até a conexão."
    else:
        text = "Ative o LINK no Traktor primeiro. A conexão é ativada manualmente a cada abertura do BEATLIGHT."
    self.link_notice.setText(text)
