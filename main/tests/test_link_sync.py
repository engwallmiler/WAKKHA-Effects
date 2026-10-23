"""Relógio externo não é evidência acústica nem comando de transporte."""
from dataclasses import replace
import math
from time import monotonic, sleep
import pytest
from beatlight.contracts import MonitorSnapshot, StructureFeatures, KickEvent
from beatlight.music.structure import StructureTracker
from beatlight.sync.link import LinkRuntime, LinkSnapshot
from beatlight.sync.timeline import apply_link, link_grid


def monitor(at=10):
    structure = StructureTracker().process(StructureFeatures(1, at, -40, -30, -25, .3, False))
    return MonitorSnapshot(1, (), (-25,), (-10,), False, False, at, at, 0, 0, 0, structure=structure)


def connected(at=10, beat=16.25, tempo=120, revision=1):
    return LinkSnapshot(at, "connected", tempo, beat, 1, revision, .2)


def test_link_drives_grid_and_eight_step_cycle_without_creating_kicks_or_drop():
    original = monitor()
    routed = apply_link(original, connected(), 10.125)
    assert routed.timing_source == routed.structure.timing_source == "link"
    assert routed.beat.bpm == 120 and routed.beat.phase == pytest.approx(.5)
    assert routed.structure.phrase_kick == 1
    assert routed.structure.grid.next_kick_at == pytest.approx(10.375)
    assert routed.structure.state == original.structure.state
    assert routed.structure.events == original.structure.events
    assert routed.structure.confirmed_kicks == original.structure.confirmed_kicks == ()
    assert routed.kicks is original.kicks and routed.kick_verification is original.kick_verification
    assert original.timing_source == "audio"  # snapshot acústico não é alterado
    steps = {apply_link(original, connected(10+t, 16.25+t*2), 10+t).structure.phrase_kick for t in range(4)}
    assert steps == {1, 3, 5, 7}
    assert apply_link(original, connected(14, 24.25), 14).structure.phrase_kick == 1


@pytest.mark.parametrize("link,at", [(LinkSnapshot(), 10), (LinkSnapshot(10, "waiting", 120, 0, 0), 10),
    (connected(), 10.501), (connected(), 9.74), (replace(connected(), state="error"), 10),
    (replace(connected(), tempo=math.nan), 10), (replace(connected(), beat=math.inf), 10)])
def test_unavailable_or_stale_link_returns_to_original_audio_snapshot(link, at):
    original = monitor()
    assert apply_link(original, link, at) is original
    assert link_grid(link, at) is None


def test_positive_offset_delays_visual_clock_and_changes_revision():
    base = link_grid(connected(), 10)
    delayed = link_grid(connected(), 10, 50)
    assert delayed.phase == pytest.approx(base.phase - .1)
    assert delayed.next_kick_at == pytest.approx(base.next_kick_at + .05)
    assert delayed.revision != base.revision
    assert link_grid(connected(), 9.9).phase == pytest.approx(.05)  # descritor acústico anterior à leitura
    with pytest.raises(ValueError):
        link_grid(connected(), 10, math.nan)


class Backend:
    closed = False
    peers = 1
    def read(self):
        now = monotonic()
        return now, 120.0, now * 2, self.peers, .1
    def close(self):
        self.closed = True


def until(predicate):
    deadline = monotonic() + 2
    while not predicate() and monotonic() < deadline:
        sleep(.01)
    assert predicate()


def test_runtime_is_off_by_default_publishes_fresh_clock_and_releases_backend():
    backend = Backend()
    runtime = LinkRuntime(lambda: backend)
    assert runtime.snapshot().state == "disabled"
    try:
        runtime.start()
        until(lambda: runtime.snapshot().usable(monotonic()))
        initial = runtime.snapshot()
        runtime.start()  # idempotente, não cria outro participante
        backend.peers = 0
        until(lambda: runtime.snapshot().state == "waiting")
        assert not runtime.snapshot().usable(monotonic())
        backend.peers = 1
        until(lambda: runtime.snapshot().state == "connected")
        assert runtime.snapshot().revision > initial.revision
    finally:
        runtime.stop()
    assert backend.closed and runtime.snapshot().state == "disabled"


def test_dependency_error_is_isolated_and_retry_is_possible():
    def missing():
        raise ImportError("aalink ausente")
    runtime = LinkRuntime(missing)
    runtime.start()
    until(lambda: runtime.snapshot().state == "error")
    assert "aalink ausente" in runtime.snapshot().error
    runtime._factory = Backend
    try:
        runtime.start()
        until(lambda: runtime.snapshot().state == "connected")
    finally:
        runtime.stop()


def test_silence_and_audio_errors_are_preserved_under_link():
    original = monitor()
    original = replace(original, silent=True, kick_error="sem detector",
        structure=replace(original.structure, state="silence"))
    routed = apply_link(original, connected(), 10)
    assert routed.silent and routed.structure.state == "silence"
    assert routed.kick_error == "sem detector" and routed.structure.drop_kicks == 0
