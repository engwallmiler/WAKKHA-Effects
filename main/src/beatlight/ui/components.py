from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout


def label(text: str, kind: str = "", wrap: bool = False) -> QLabel:
    item = QLabel(text)
    if kind:
        item.setObjectName(kind)
    item.setWordWrap(wrap)
    return item


def card(title: str = "", subtitle: str = ""):
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 17, 20, 17)
    layout.setSpacing(10)
    if title:
        layout.addWidget(label(title, "section"))
    if subtitle:
        layout.addWidget(label(subtitle, "muted", True))
    return frame, layout


def metric(title: str, footnote: str):
    frame, layout = card()
    layout.addWidget(label(title, "eyebrow"))
    value = label("—", "value")
    layout.addWidget(value)
    layout.addWidget(label(footnote, "muted"))
    return frame, value


def stable_label(text: str, kind: str = "", lines: int = 1):
    """Reserva linhas fixas; texto em tempo real não participa do tamanho do layout."""
    item = label(text, kind, lines > 1)
    item.setMinimumWidth(0)
    item.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
    item.setFixedHeight(item.fontMetrics().lineSpacing() * lines + 6)
    item.setToolTip(text)
    return item
