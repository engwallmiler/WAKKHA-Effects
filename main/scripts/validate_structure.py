"""Validação offline de uma composição sintética; não captura nem reproduz áudio."""
import json
from pathlib import Path
import sys
from time import perf_counter
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from beatlight.audio.demo import structure_demo_samples
from beatlight.contracts import AudioBlock, LightingInput
from beatlight.dsp.pipeline import AudioAnalyzer
from beatlight.lighting.config import LightConfig, LightingControls
from beatlight.lighting.engine import LightingEngine


def validate(seconds=28):
    rate, size = 48000, 512
    analyzer, engine = AudioAnalyzer(), LightingEngine()
    controls = LightingControls(LightConfig(light_effect="musical", light_transition_ms=0), armed=True)
    transitions, drop_counts, tension, frame_times = [], [], {}, []
    state = None
    started = perf_counter()
    for sequence, first in enumerate(range(0, int(seconds * rate), size)):
        t = np.arange(first, min(first + size, int(seconds * rate))) / rate
        samples = structure_demo_samples(t)
        samples.setflags(write=False)
        at = 100 + first / rate
        block = AudioBlock("structure:offline", samples, rate, 2, sequence, len(samples), at, at + len(samples) / rate)
        snapshot = analyzer.process(block)
        music = snapshot.structure
        if not music:
            continue
        light = engine.render(LightingInput(True, True, snapshot.kicks.events, snapshot.beat, music, texture=snapshot.texture,
            confirmed_kicks=snapshot.kick_verification.confirmed_events if snapshot.kick_verification else (),
            kick_confirmed_at=snapshot.kick_verification.last_confirmed_at if snapshot.kick_verification else None), controls, at + len(samples) / rate)
        if music.state != state:
            transitions.append(dict(at=round(music.updated_at - 100, 3), state=music.state,
                tension=round(music.tension, 3), confidence=round(music.confidence, 3),
                reason=music.reason, peak_intensity=max(s.intensity for s in light.states)))
            state = music.state
        tension[music.state] = max(tension.get(music.state, 0), music.tension)
        if music.state == "drop" and (not drop_counts or drop_counts[-1] != music.drop_kicks):
            drop_counts.append(music.drop_kicks)
        frame_times.append(snapshot.processing_ms)
    return dict(source="synthetic_composition_offline", physical_output=False, seconds=seconds,
        elapsed_processing_seconds=perf_counter() - started, transitions=transitions, drop_kicks=drop_counts,
        max_tension=tension, mean_block_ms=float(np.mean(frame_times)), p99_block_ms=float(np.percentile(frame_times, 99)),
        continuity_errors=snapshot.continuity_errors, errors=dict(dsp=snapshot.analysis_error,
            kick=snapshot.kick_error, beat=snapshot.beat_error, structure=snapshot.structure_error, texture=snapshot.texture_error, verification=snapshot.kick_verification_error))


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
