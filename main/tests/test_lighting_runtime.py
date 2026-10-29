from dataclasses import replace
from time import monotonic, sleep
from types import SimpleNamespace
import pytest
from beatlight.core.lighting_runtime import LightingRuntime
from beatlight.lighting.config import LightConfig, LightingControls


def wait_for(condition, timeout=2):
    end = monotonic() + timeout
    while monotonic() < end:
        if condition():
            return
        sleep(0.005)
    assert condition()


def provider():
    return None, SimpleNamespace(state="stopped", audio_age=0)


def test_worker_runs_without_gui_and_stops_dark():
    controls = LightingControls(LightConfig(light_effect="ambient", light_transition_ms=0), armed=True)
    runtime = LightingRuntime(provider, controls)
    runtime.start()
    try:
        wait_for(lambda: runtime.snapshot().frame_id > 4 and runtime.snapshot().status == "ambient")
        assert runtime.running
        assert any(s.intensity > 0 for s in runtime.snapshot().states)
        runtime.set_controls(replace(controls, blackout=True))
        wait_for(lambda: runtime.snapshot().status == "blackout")
        assert all(s.intensity == 0 for s in runtime.snapshot().states)
    finally:
        runtime.stop()
    assert not runtime.running
    assert runtime.snapshot().status == "stopped"
    assert all(s.intensity == 0 for s in runtime.snapshot().states)


def test_suspended_legacy_preview_does_no_provider_work_and_resumes():
    calls=[]
    def counted():calls.append(1);return provider()
    runtime=LightingRuntime(counted,LightingControls(LightConfig(light_effect='ambient'),armed=True))
    runtime.set_suspended(True);runtime.start()
    try:
        wait_for(lambda:runtime.snapshot().status=='disabled')
        sleep(.08);assert not calls
        runtime.set_suspended(False);wait_for(lambda:len(calls)>=3)
        runtime.set_suspended(True);wait_for(lambda:runtime.snapshot().status=='disabled')
        before=len(calls);sleep(.08);assert len(calls)==before
    finally:runtime.stop()
    assert not runtime.running


def test_engine_failure_is_latched_dark_until_a_control_changes(monkeypatch, caplog):
    runtime = LightingRuntime(provider, LightingControls(LightConfig(light_effect="ambient"), armed=True))
    original = runtime.engine.render
    def fail(*args):
        raise RuntimeError("lighting-test-failure")
    monkeypatch.setattr(runtime.engine, "render", fail)
    runtime.start()
    try:
        wait_for(lambda: bool(runtime.snapshot().error))
        assert runtime.running  # falha de iluminação não encerra o processo
        assert all(s.intensity == 0 for s in runtime.snapshot().states)
        sleep(0.08)
        assert sum(r.message == "lighting_engine_failed" for r in caplog.records) == 1
        monkeypatch.setattr(runtime.engine, "render", original)
        runtime.set_controls(replace(runtime.controls(), manual=True))
        wait_for(lambda: runtime.snapshot().status == "manual" and not runtime.snapshot().error)
    finally:
        runtime.stop()


def test_provider_failure_keeps_blackout_and_outputs_dark(caplog):
    def unavailable():
        raise RuntimeError("provider-test-failure")
    controls = LightingControls(armed=True, blackout=True)
    runtime = LightingRuntime(unavailable, controls)
    runtime.start()
    try:
        wait_for(lambda: runtime.snapshot().status == "error")
        assert runtime.snapshot().blackout
        assert all(s.intensity == 0 for s in runtime.snapshot().states)
    finally:
        runtime.stop()


def test_default_controls_are_disarmed_and_idempotent_start_stop():
    runtime = LightingRuntime(provider)
    runtime.start()
    first_thread = runtime._thread
    runtime.start()
    assert runtime._thread is first_thread
    assert not runtime.controls().armed and not runtime.controls().manual
    runtime.stop()
    runtime.stop()
    assert all(s.intensity == 0 for s in runtime.snapshot().states)


@pytest.mark.parametrize("rate", [0, 1000, True])
def test_invalid_worker_rate_rejected(rate):
    with pytest.raises(ValueError):
        LightingRuntime(provider, rate_hz=rate)


def test_worker_routes_confirmed_kicks_and_keeps_texture_independent(block_factory):
    from beatlight.contracts import KickEvent,KickVerificationSnapshot,TextureSnapshot
    from beatlight.dsp.pipeline import AudioAnalyzer
    base=AudioAnalyzer().process(block_factory([[0,0]]*2048))
    now=monotonic()
    raw=KickEvent(now,now,1,0.95)
    verification=KickVerificationSnapshot(now,0,1,0,0,0,(),(raw,),())
    current=[replace(base,kicks=replace(base.kicks,events=(raw,),last_event=raw),kick_verification=verification)]
    status=SimpleNamespace(state="running",audio_age=0)
    controls=LightingControls(LightConfig(light_transition_ms=0),armed=True)
    runtime=LightingRuntime(lambda:(current[0],status),controls)
    runtime.start()
    try:
        wait_for(lambda:runtime.snapshot().frame_id>3)
        assert all(f.intensity==0 for f in runtime.snapshot().states)
        now=monotonic()
        event=KickEvent(now-0.12,now-0.1,1,0.95)
        current[0]=replace(current[0],kick_verification=replace(verification,updated_at=now,confirmed_count=1,confirmed_events=(event,),last_confirmed_at=now))
        wait_for(lambda:any(f.intensity>0.3 for f in runtime.snapshot().states))
        now=monotonic()
        current[0]=replace(current[0],structure_error="indisponível",beat_error="indisponível",
            texture=TextureSnapshot(now,-20,0.8,0.1,0.7,0.7,4,0.2),texture_error="")
        runtime.set_controls(replace(controls,config=replace(controls.config,light_effect="bass_flow")))
        wait_for(lambda:runtime.snapshot().effect=="bass_flow" and any(f.intensity>0.2 for f in runtime.snapshot().states))
    finally:
        runtime.stop()
