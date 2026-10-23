from dataclasses import replace
import numpy as np
import pytest
from beatlight.audio.demo import structure_demo_samples
from beatlight.contracts import AudioBlock, LightingInput
from beatlight.dsp.config import DspConfig
from beatlight.dsp.pipeline import AudioAnalyzer
from beatlight.lighting.config import LightConfig, LightingControls
from beatlight.lighting.engine import LightingEngine


def process_composition(gain):
    analyzer, lighting = AudioAnalyzer(), LightingEngine()
    controls = LightingControls(LightConfig(light_effect="musical", light_transition_ms=0), armed=True)
    changes, counts, tensions, peak = [], set(), [], 0.0
    for seq, first in enumerate(range(0, 48000 * 25, 512)):
        t = np.arange(first, first + 512) / 48000
        x = structure_demo_samples(t) * gain
        x.setflags(write=False)
        at = 100 + first / 48000
        snapshot = analyzer.process(AudioBlock("demo", x, 48000, 2, seq, 512, at, at + 512 / 48000))
        s = snapshot.structure
        if not s:
            continue
        assert not snapshot.structure_error
        assert not snapshot.kick_error and not snapshot.beat_error
        assert snapshot.continuity_errors == 0
        if not changes or changes[-1][1] != s.state:
            changes.append((s.updated_at - 100, s.state))
        frame = lighting.render(LightingInput(True, True, snapshot.kicks.events, snapshot.beat, s), controls, at + 512 / 48000)
        assert all(0 <= state.intensity <= 0.8 for state in frame.states)
        if s.state == "buildup":
            tensions.append(s.tension)
        if s.state == "drop":
            counts.add(s.drop_kicks)
            peak = max(peak, max(state.intensity for state in frame.states))
    return changes, counts, tensions, peak


@pytest.mark.parametrize("gain", [1.0, 0.25])
def test_complete_audio_path_builds_and_releases_energy_after_eight_kicks(gain):
    changes, counts, tensions, peak = process_composition(gain)
    assert [state for _, state in changes] == ["warming", "groove", "breakdown", "buildup", "drop", "groove"]
    assert dict((state, at) for at, state in changes)["drop"] == pytest.approx(20, abs=0.3)
    assert counts == set(range(1, 9))
    assert tensions[-1] > tensions[0] + 0.3
    assert peak > 0.7
    assert changes[-1][0] == pytest.approx(24, abs=0.3)


def test_structure_ignores_user_inspection_filters_and_stereo_phase_cancellation():
    raw = AudioAnalyzer()
    filtered = AudioAnalyzer(config=DspConfig(filter_mode="lowpass", filter_high_hz=150))
    for seq in range(94):
        t = (np.arange(512) + seq * 512) / 48000
        signal = 0.3 * np.sin(2 * np.pi * 5000 * t)
        x = np.column_stack((signal, -signal)).astype(np.float32)
        x.setflags(write=False)
        block = AudioBlock("antiphase", x, 48000, 2, seq, 512, 10 + seq * 512 / 48000, 11)
        a, b = raw.process(block), filtered.process(block)
    assert a.structure == b.structure
    assert a.structure.brightness > 0.5
    assert b.spectral.total_rms_db < a.spectral.total_rms_db - 40


def test_structural_failure_is_isolated_logged_once_and_recovers_on_source_change(block_factory, monkeypatch, caplog):
    analyzer = AudioAnalyzer()
    original = analyzer._structure.process
    def broken(*args):
        raise RuntimeError("Falha estrutural simulada")
    monkeypatch.setattr(analyzer._structure, "process", broken)
    for seq in range(5):
        snapshot = analyzer.process(block_factory(np.full((2048, 2), 0.2), sequence=seq))
        assert snapshot.rms_db[0] == pytest.approx(-13.9794, abs=0.001)
        assert snapshot.kicks is not None and snapshot.beat is not None
        assert snapshot.structure is None
        assert snapshot.structure_error == "Falha estrutural simulada"
    assert sum(r.message == "structure_analysis_failed" for r in caplog.records) == 1
    monkeypatch.setattr(analyzer._structure, "process", original)
    snapshot = analyzer.process(replace(block_factory(np.zeros((2048, 2)), sequence=5), source_id="other"))
    assert snapshot.structure is not None and not snapshot.structure_error


def test_discontinuity_resets_structural_context(block_factory):
    analyzer = AudioAnalyzer()
    analyzer.process(block_factory(np.ones((2048, 2)), sequence=0))
    analyzer._structure._learned = True
    analyzer._structure._state = "drop"
    analyzer._structure._drop_count = 7
    after = analyzer.process(block_factory(np.zeros((2048, 2)), sequence=3, discontinuity=True))
    assert after.structure.state == "warming"
    assert after.structure.drop_id == after.structure.drop_kicks == 0


def test_missing_callbacks_reset_windows_on_resume_even_with_contiguous_sequence():
    analyzer = AudioAnalyzer()
    samples = np.ones((2048, 2), dtype=np.float32) * 0.1
    samples.setflags(write=False)
    analyzer.process(AudioBlock("test", samples, 48000, 2, 0, 2048, 10, 10.05))
    analyzer._structure._state = "buildup"
    resumed = analyzer.process(AudioBlock("test", samples, 48000, 2, 1, 2048, 20, 20.05))
    assert resumed.structure.state == "warming"
    assert resumed.structure.updated_at > 20
    assert resumed.continuity_errors == 1
    assert resumed.kicks.events == ()


def test_real_audio_roll_with_continuing_kicks_and_bass_enters_buildup():
    analyzer = AudioAnalyzer()
    states = []
    for seq, first in enumerate(range(0, 48000 * 11, 512)):
        t = np.arange(first, first + 512) / 48000
        x = structure_demo_samples(t)
        rolling = t >= 6
        roll = 0.35 * np.exp(-((t * 8) % 1) * 14) * np.sin(2 * np.pi * 1400 * t)
        x += (roll * rolling)[:, None].astype(np.float32)
        # Preserva o kick após 8 s; esta variação testa subida sem breakdown prévio.
        kick_env = np.exp(-((t * 2) % 1) * 12) * (t >= 8)
        x[:, 0] += (0.45 * kick_env * np.sin(2 * np.pi * 70 * t)).astype(np.float32)
        x[:, 1] += (0.4 * kick_env * np.sin(2 * np.pi * 85 * t)).astype(np.float32)
        x.setflags(write=False)
        at = 100 + first / 48000
        snapshot = analyzer.process(AudioBlock("roll-groove", x, 48000, 2, seq, 512, at, at + 512 / 48000))
        if snapshot.structure and first > 48000 * 6:
            states.append(snapshot.structure)
    assert any(s.state == "buildup" for s in states)
    assert states[-1].state == "buildup"
    assert max(s.roll_rate for s in states) > 6
    assert all(s.state != "drop" for s in states)
