"""Logs estruturados e limitados em disco; áudio bruto nunca é persistido."""
from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {"time": datetime.now(timezone.utc).isoformat(), "level": record.levelname,
                "module": record.name, "event": record.getMessage()}
        for key in ("device", "rate", "channels", "block_size", "reason"):
            if hasattr(record, key):
                data[key] = getattr(record, key)
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


def configure_logging(directory: Path) -> str:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(directory / "beatlight.jsonl", maxBytes=2_000_000,
                                      backupCount=3, encoding="utf-8")
        handler.setFormatter(JsonFormatter())
        logger = logging.getLogger("beatlight")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        return ""
    except OSError as exc:
        return f"Logs em disco indisponíveis: {exc}"
