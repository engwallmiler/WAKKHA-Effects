"""Tema nativo Qt, sem recursos externos ou dependências de rede."""
STYLE = """
QWidget { background: #101316; color: #e7ebef; font-family: 'Segoe UI'; font-size: 13px; }
QLabel { background: transparent; }
QMainWindow { background: #101316; }
QFrame#sidebar { background: #15191d; border-right: 1px solid #292f35; }
QFrame#card { background: #191e23; border: 1px solid #2b3239; border-radius: 10px; }
QFrame#card QLabel, QFrame#card QWidget { background: transparent; }
QLabel#brand { font-size: 24px; font-weight: 800; letter-spacing: 2px; color: #f4f7f9; }
QLabel#eyebrow { color: #8d9aa5; font-size: 10px; font-weight: 700; letter-spacing: 2px; }
QLabel#title { font-size: 30px; font-weight: 650; color: #f4f7f9; }
QLabel#subtitle { color: #95a3af; font-size: 13px; }
QLabel#value { font-size: 27px; font-weight: 600; color: #f1f5f7; }
QLabel#metric { font-size: 20px; font-weight: 600; color: #6de9c1; }
QLabel#section { font-size: 14px; font-weight: 600; }
QLabel#muted { color: #778693; font-size: 12px; }
QLabel#badge { border: 1px solid #355b50; background: #1a302a; color: #7aebc7; border-radius: 6px; padding: 6px 10px; font-size: 10px; font-weight: 700; }
QLabel#notice { background: #20272b; border: 1px solid #323e44; border-radius: 8px; padding: 12px; color: #a9b8c3; }
QPushButton { background: #242c33; border: 1px solid #36414b; border-radius: 6px; padding: 9px 14px; font-weight: 600; }
QPushButton:hover { background: #303b45; border-color: #566773; }
QPushButton:disabled { color: #56616a; border-color: #2a3238; background: #1c2227; }
QPushButton#primary { background: #69e5bc; color: #0b2a20; border-color: #69e5bc; }
QPushButton#primary:hover { background: #9af5d6; }
QPushButton#primary:disabled { background: #2b4b40; color: #698e80; border-color: #2b4b40; }
QPushButton#stop { color: #f5b6a9; }
QPushButton#nav { text-align: left; border: 0; background: transparent; color: #92a0aa; padding: 13px 16px; font-size: 13px; }
QPushButton#nav:checked { background: #223b33; color: #7eeac6; border-left: 3px solid #6de9c1; border-radius: 3px; }
QPushButton#nav:hover { background: #232b31; }
QComboBox, QSpinBox, QDoubleSpinBox { background: #11171b; border: 1px solid #37434c; border-radius: 6px; padding: 8px 12px; min-height: 21px; }
QComboBox:disabled { color: #6c7881; }
QComboBox QAbstractItemView { background: #20282e; selection-background-color: #29483c; padding: 5px; }
QComboBox::drop-down { border: 0; width: 26px; }
QTextEdit { background: #11171b; border: 1px solid #2e3942; border-radius: 6px; color: #9baebd; font-family: 'Cascadia Code', 'Consolas'; font-size: 12px; padding: 10px; }
QScrollArea { border: 0; background: transparent; }
QScrollBar:vertical { background: #15191d; width: 9px; }
QScrollBar::handle:vertical { background: #38434c; border-radius: 4px; min-height: 25px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle { background: #101316; width: 9px; height: 9px; }
QToolTip { background: #28353e; color: #f4f7f9; border: 1px solid #4b5f6c; padding: 6px; }
"""
