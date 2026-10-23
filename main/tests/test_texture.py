from dataclasses import replace
import numpy as np
import pytest
from beatlight.contracts import AudioBlock, LightingInput
from beatlight.dsp.pipeline import AudioAnalyzer
from beatlight.lighting.config import LightConfig, LightingControls
from beatlight.lighting.engine import LightingEngine


def analyze(signal, seconds=2, analyzer=None):
    analyzer = analyzer or AudioAnalyzer()
    for seq, first in enumerate(range(0, int(48000 * seconds), 512)):
        t = np.arange(first, first + 512) / 48000
        x = signal(t)
        if x.ndim == 1:
            x = np.column_stack((x, x))
        x = x.astype(np.float32)
        x.setflags(write=False)
        at = 100 + first / 48000
        snapshot = analyzer.process(AudioBlock("texture", x, 48000, 2, seq, 512, at, at + 512/48000))
        assert not snapshot.texture_error
    return snapshot


def rich(t):
    return sum(0.06 * np.sin(2*np.pi*f*t) for f in (80, 160, 330, 700, 1500, 3200, 6500, 12000))


def test_density_responds_to_spectral_fill_and_is_stable_under_gain_change():
    sparse = analyze(lambda t: 0.3*np.sin(2*np.pi*80*t)).texture
    dense = analyze(rich).texture
    quiet = analyze(lambda t: rich(t)*0.25).texture
    assert dense.density > sparse.density + 0.25
    assert dense.occupancy > sparse.occupancy + 0.3
    assert quiet.density == pytest.approx(dense.density, abs=0.03)
    assert 0 <= sparse.density <= dense.density <= 1


def test_steady_bass_can_drive_lights_without_kicks_or_a_locked_bpm():
    snapshot = analyze(lambda t: 0.3*np.sin(2*np.pi*90*t))
    assert snapshot.beat.state != "locked"
    assert snapshot.texture.bass_level > 0.6
    engine = LightingEngine()
    cfg = LightingControls(LightConfig(light_effect="bass_flow", light_transition_ms=0), armed=True)
    result = engine.render(LightingInput(True, True, texture=snapshot.texture, confirmed_kicks=()), cfg, snapshot.texture.updated_at)
    assert min(f.intensity for f in result.states) > 0.2


def test_dense_highs_do_not_need_bass_to_drive_the_density_scene():
    snapshot = analyze(lambda t: sum(0.07*np.sin(2*np.pi*f*t) for f in (1000, 2100, 4300, 8800, 14000)))
    assert snapshot.texture.bass_level < 0.1
    assert snapshot.texture.density > 0.3
    cfg = LightingControls(LightConfig(light_effect="density_wash", light_transition_ms=0), armed=True)
    frame = LightingEngine().render(LightingInput(True, True, texture=snapshot.texture, confirmed_kicks=()), cfg, snapshot.texture.updated_at)
    assert any(f.intensity > 0.05 for f in frame.states)


def test_texture_preserves_opposite_phase_stereo():
    normal = analyze(rich).texture
    opposite = analyze(lambda t: np.column_stack((rich(t), -rich(t)))).texture
    assert opposite.bass_db == pytest.approx(normal.bass_db)
    assert opposite.density == pytest.approx(normal.density)


def test_structure_failure_does_not_stop_texture_updates(monkeypatch):
    analyzer = AudioAnalyzer()
    def broken(*args):
        raise RuntimeError("structure-failure")
    monkeypatch.setattr(analyzer._structure, "process", broken)
    result = analyze(rich, analyzer=analyzer)
    assert result.structure_error == "structure-failure"
    assert result.texture.updated_at > 101.8 and result.texture.density > 0.5
    assert result.kick_verification is None


def test_gap_resets_texture_without_holding_previous_bass():
    analyzer = AudioAnalyzer()
    analyze(rich, analyzer=analyzer)
    x = np.zeros((2048,2), dtype=np.float32)
    after = analyzer.process(AudioBlock("texture", x, 48000,2,500,2048,110,110.05,True))
    assert after.texture.bass_level == after.texture.density == 0
    assert after.kick_verification.confirmed_count == 0


def test_optional_texture_failure_is_isolated_and_logged_once(monkeypatch,caplog):
    analyzer=AudioAnalyzer()
    analyze(rich,seconds=0.1,analyzer=analyzer)
    def broken(*args):
        raise RuntimeError("texture-failure")
    monkeypatch.setattr(analyzer._texture,"process",broken)
    # Mantém o mesmo fluxo; uma falha da textura não encerra kicks/estrutura.
    for seq in range(10,20):
        t=(np.arange(512)+seq*512)/48000
        x=np.column_stack((rich(t),rich(t))).astype(np.float32)
        at=100+seq*512/48000
        result=analyzer.process(AudioBlock("texture",x,48000,2,seq,512,at,at+512/48000))
    assert result.texture is None and result.texture_error=="texture-failure"
    assert result.structure is not None and not result.structure_error and result.kicks is not None
    assert sum(r.message=="texture_analysis_failed" for r in caplog.records)==1
