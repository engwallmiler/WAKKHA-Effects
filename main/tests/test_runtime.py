from time import monotonic, sleep
from threading import enumerate as threads
import pytest
from beatlight.audio.synthetic import SyntheticSource
from beatlight.core.runtime import CaptureRuntime


def wait_for(predicate, timeout=3):
    until = monotonic() + timeout
    while monotonic() < until:
        if predicate():
            return
        sleep(0.01)
    assert predicate(), "Condição não atingida no prazo"


def test_synthetic_pipeline_and_repeated_start_stop():
    runtime = CaptureRuntime()
    for _ in range(5):
        source = SyntheticSource()
        try:
            runtime.start(source, source.devices()[0], 512)
            wait_for(lambda: runtime.snapshot() is not None)
            assert runtime.status().state == "running"
            assert runtime.status().stream_format.sample_rate == 48000
            assert runtime.status().blocks > 0
            assert not runtime.snapshot().silent
        finally:
            runtime.stop()
        assert runtime.status().state == "stopped"
    runtime.stop()
    assert not [t for t in threads() if t.name in ("audio-analysis", "synthetic-input")]


def test_silent_source_is_not_treated_as_disconnected():
    runtime = CaptureRuntime()
    source = SyntheticSource(silence=True)
    try:
        runtime.start(source, source.devices()[0], 1024)
        wait_for(lambda: runtime.snapshot() is not None)
        assert runtime.snapshot().silent
        assert runtime.status().state == "running"
    finally:
        runtime.stop()


class FailingSource(SyntheticSource):
    def start(self, *args):
        raise OSError("Dispositivo desconectado")


def test_device_error_allows_recovery():
    runtime = CaptureRuntime()
    source = FailingSource()
    with pytest.raises(RuntimeError, match="desconectado"):
        runtime.start(source, source.devices()[0], 512)
    assert runtime.status().state == "error"
    runtime.stop()
    good = SyntheticSource()
    try:
        runtime.start(good, good.devices()[0], 512)
        wait_for(lambda: runtime.snapshot() is not None)
        assert runtime.status().state == "running"
    finally:
        runtime.stop()


class DisconnectingSource(SyntheticSource):
    def poll_error(self):
        return "Saída removida durante a captura"


def test_midstream_disconnect_cleans_up_and_preserves_error():
    runtime = CaptureRuntime()
    source = DisconnectingSource()
    try:
        try:
            runtime.start(source, source.devices()[0], 512)
        except RuntimeError:
            pass  # falha pode chegar antes da confirmação de abertura
        wait_for(lambda: runtime.status().state == "error")
        assert "removida" in runtime.status().error
        wait_for(lambda: not any(t.name == "synthetic-input" for t in threads()))
    finally:
        runtime.stop()


def test_invalid_block_size_is_rejected():
    source = SyntheticSource()
    with pytest.raises(ValueError):
        CaptureRuntime().start(source, source.devices()[0], 777)


def test_slow_consumer_keeps_queue_bounded_and_records_drops():
    from beatlight.dsp.meter import LevelAnalyzer
    class SlowAnalyzer:
        def __init__(self):
            self.levels = LevelAnalyzer()
        def process(self, block):
            sleep(0.03)
            return self.levels.process(block)
    runtime = CaptureRuntime(queue_capacity=2, analyzer_factory=SlowAnalyzer)
    source = SyntheticSource()
    try:
        runtime.start(source, source.devices()[0], 256)
        wait_for(lambda: runtime.status().dropped_blocks >= 5)
        assert runtime.status().queue_depth <= 2
        wait_for(lambda: runtime.snapshot() is not None and runtime.snapshot().continuity_errors > 0)
        assert runtime.status().state == "running"
    finally:
        runtime.stop()
