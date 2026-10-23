from time import monotonic
import numpy as np
import pytest
from beatlight.audio.wasapi import WasapiSource


class FakeStream:
    def __init__(self, callback, module):
        self.callback = callback
        self.module = module
        self.active = False
        self.closed = False

    def get_input_latency(self):
        return 0.012

    def start_stream(self):
        self.active = True

    def stop_stream(self):
        self.active = False

    def close(self):
        self.closed = True

    def is_active(self):
        return self.active


class FakePortAudio:
    def __init__(self, module):
        self.module = module
        self.terminated = False
        module.instances.append(self)

    def get_default_wasapi_loopback(self):
        info = self.module.info()
        info["index"] = self.module.default_index
        return info

    def get_loopback_device_info_generator(self):
        return iter([self.module.info()] if self.module.present else [])

    def open(self, **kwargs):
        self.module.open_kwargs = kwargs
        if self.module.fail_open:
            raise OSError("Formato não suportado")
        self.module.stream = FakeStream(kwargs["stream_callback"], self.module)
        return self.module.stream

    def terminate(self):
        self.terminated = True


class FakeModule:
    paFloat32, paContinue, paAbort = 1, 0, 2
    def __init__(self):
        self.instances = []
        self.index = 10
        self.default_index = 10
        self.present = True
        self.rate = 48000
        self.fail_open = False

    def info(self):
        return {"index": self.index, "name": "Realtek Speakers [Loopback]",
                "maxInputChannels": 2, "defaultSampleRate": self.rate}

    def PyAudio(self):
        return FakePortAudio(self)


def test_discovery_format_timestamps_and_index_refresh():
    lib = FakeModule()
    source = WasapiSource(lib)
    device = source.devices()[0]
    assert device.is_default
    assert device.name == "Realtek Speakers"
    assert lib.instances[0].terminated
    lib.index = 42  # reconexão mudou índice, mas identidade continua válida
    blocks = []
    try:
        fmt = source.start(device, 512, blocks.append)
        assert fmt.sample_format == "float32"
        assert fmt.input_latency == 0.012
        assert lib.open_kwargs["input_device_index"] == 42
        assert lib.open_kwargs["channels"] == 2
        for _ in range(2):
            result = lib.stream.callback(np.zeros((512, 2), np.float32).tobytes(), 512,
                                         {"current_time": 50, "input_buffer_adc_time": 49.99}, 0)
            assert result == (None, lib.paContinue)
        assert blocks[0].samples.shape == (512, 2)
        assert not blocks[0].samples.flags.writeable
        assert blocks[1].sequence == 1
        assert blocks[0].acquired_at <= blocks[0].received_at <= monotonic()
        assert source.poll_error() is None
    finally:
        source.stop()
    source.stop()
    assert lib.stream.closed
    assert lib.instances[-1].terminated


def test_driver_overflow_marks_block_discontinuous():
    lib = FakeModule()
    source = WasapiSource(lib)
    blocks = []
    try:
        source.start(source.devices()[0], 512, blocks.append)
        lib.stream.callback(np.zeros((512, 2), np.float32).tobytes(), 512, {}, 2)
        assert blocks[0].discontinuity
        assert blocks[0].status_flags == 2
    finally:
        source.stop()


def test_callback_error_aborts_stream_and_is_reported():
    lib = FakeModule()
    source = WasapiSource(lib)
    try:
        source.start(source.devices()[0], 512, lambda block: None)
        assert lib.stream.callback(b"bad-data", 512, {}, 0) == (None, lib.paAbort)
        assert "callback" in source.poll_error()
    finally:
        source.stop()


def test_failed_open_releases_portaudio_and_allows_restart():
    lib = FakeModule()
    source = WasapiSource(lib)
    device = source.devices()[0]
    lib.fail_open = True
    with pytest.raises(OSError):
        source.start(device, 512, lambda block: None)
    assert lib.instances[-1].terminated
    lib.fail_open = False
    source.start(device, 512, lambda block: None)
    source.stop()


def test_inactive_stream_reports_disconnect():
    lib = FakeModule()
    source = WasapiSource(lib)
    try:
        source.start(source.devices()[0], 512, lambda block: None)
        lib.stream.active = False
        assert "interrompeu" in source.poll_error()
    finally:
        source.stop()


def test_device_health_detects_removal_without_waiting_for_stream_failure():
    from time import sleep
    lib = FakeModule()
    source = WasapiSource(lib, health_interval=0.01)
    try:
        source.start(source.devices()[0], 512, lambda block: None)
        lib.present = False
        deadline = monotonic() + 1
        while source.poll_error() is None and monotonic() < deadline:
            sleep(0.005)
        assert "removida" in source.poll_error()
    finally:
        source.stop()


def test_default_change_reports_notice_and_keeps_selected_capture():
    from time import sleep
    lib = FakeModule()
    source = WasapiSource(lib, health_interval=0.01)
    try:
        source.start(source.devices()[0], 512, lambda block: None)
        lib.default_index = 99
        deadline = monotonic() + 1
        notice = None
        while notice is None and monotonic() < deadline:
            sleep(0.005)
            notice = source.poll_notice()
        assert "padrão do Windows mudou" in notice
        assert source.poll_error() is None
        assert lib.stream.active
    finally:
        source.stop()


@pytest.mark.parametrize("rate", [44100, 48000])
def test_native_sample_rate_is_respected_without_resampling(rate):
    lib = FakeModule()
    lib.rate = rate
    source = WasapiSource(lib)
    try:
        device = source.devices()[0]
        fmt = source.start(device, 1024, lambda block: None)
        assert fmt.sample_rate == rate
        assert lib.open_kwargs["rate"] == rate
        assert fmt.block_size == 1024
    finally:
        source.stop()
