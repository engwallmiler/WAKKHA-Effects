from dataclasses import replace
import pytest
from beatlight.contracts import LightingInput
from beatlight.lighting.engine import LightingEngine
from beatlight.lighting.config import LightConfig, LightingControls
from beatlight.sync.timeline import apply_link
from test_link_sync import connected, monitor


def test_lighting_uses_link_phase_without_kicks_and_repeats_after_eight_beats():
    engine = LightingEngine()
    controls = LightingControls(LightConfig(light_effect="phrase_show", light_transition_ms=0,
        light_phrase_pattern="chase", light_phrase_prepare="none"), armed=True)
    frames = []
    for i in range(16):
        at = 10 + i * .5
        raw = monitor(at)
        raw = replace(raw, structure=replace(raw.structure, state="groove", energy=.7))
        routed = apply_link(raw, connected(at, 16.02 + i), at)
        data = LightingInput(True, True, (), routed.beat, routed.structure, confirmed_kicks=())
        frames.append(engine.render(data, controls, at))
    assert [f.phrase_step for f in frames] == list(range(1, 9)) * 2
    for first, second in zip(frames[:8], frames[8:]):
        assert [s.intensity for s in first.states[:4]] == pytest.approx([s.intensity for s in second.states[:4]])
    assert len({max(range(4), key=lambda j:f.states[j].intensity) for f in frames}) == 4
    assert all(f.status != "drop" for f in frames)
    dark = engine.render(replace(data, audio_fresh=False), controls, at+.1)
    assert all(s.intensity == 0 for s in dark.states)
