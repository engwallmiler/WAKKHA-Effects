"""Execução a partir do checkout, inclusive antes de instalar o pacote."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from beatlight.__main__ import main
raise SystemExit(main())
