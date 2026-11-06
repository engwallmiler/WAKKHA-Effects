import json
import logging
from datetime import datetime
from beatlight.diagnostics.logging import JsonFormatter
from beatlight.diagnostics.pc_time import local_time


def test_structured_log_preserves_context_and_unicode():
    record = logging.LogRecord("beatlight.audio", logging.INFO, __file__, 10,
                               "capture_started", (), None)
    record.device = "Altofalantes • Realtek"
    record.rate = 48000
    data = json.loads(JsonFormatter().format(record))
    assert data["event"] == "capture_started"
    assert data["device"] == "Altofalantes • Realtek"
    assert data["rate"] == 48000
    assert datetime.fromisoformat(data['time'])==local_time(record.created)
    assert datetime.fromisoformat(data['time']).utcoffset()==local_time(record.created).utcoffset()
    assert data['utc'].endswith('+00:00')
