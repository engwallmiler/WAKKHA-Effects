import json
import logging
from beatlight.diagnostics.logging import JsonFormatter


def test_structured_log_preserves_context_and_unicode():
    record = logging.LogRecord("beatlight.audio", logging.INFO, __file__, 10,
                               "capture_started", (), None)
    record.device = "Altofalantes • Realtek"
    record.rate = 48000
    data = json.loads(JsonFormatter().format(record))
    assert data["event"] == "capture_started"
    assert data["device"] == "Altofalantes • Realtek"
    assert data["rate"] == 48000
    assert data["time"].endswith("+00:00")
