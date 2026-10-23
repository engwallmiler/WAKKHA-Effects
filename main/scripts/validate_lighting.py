"""Valida áudio sintético e iluminação abstrata; não reproduz nem transmite nada."""
import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
from time import monotonic, sleep
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from beatlight.audio.synthetic import SyntheticSource
from beatlight.core.runtime import CaptureRuntime
from beatlight.core.lighting_runtime import LightingRuntime
from beatlight.lighting.config import LightConfig, LightingControls


def wait_for(condition, timeout=2):
    end = monotonic() + timeout
    while monotonic() < end:
        if condition():
            return
        sleep(0.002)
    raise RuntimeError("Prazo de comando de iluminação excedido.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=12)
    args = parser.parse_args()
    if not 6 <= args.seconds <= 120:
        parser.error("Use uma duração entre 6 e 120 segundos.")
    audio = CaptureRuntime()
    lights = LightingRuntime(lambda: (audio.snapshot(), audio.status()),
        LightingControls(LightConfig(light_effect="beat_pulse", light_transition_ms=0), armed=True))
    source = SyntheticSource()
    peak, lighting_peak_ms, sampled_frames, previous = 0.0, 0.0, 0, -1
    try:
        audio.start(source, source.devices()[0], 512)
        lights.start()
        deadline = monotonic() + args.seconds
        while monotonic() < deadline:
            frame = lights.snapshot()
            if frame.frame_id != previous:
                previous = frame.frame_id
                sampled_frames += 1
                peak = max(peak, max(s.intensity for s in frame.states))
                lighting_peak_ms = max(lighting_peak_ms, frame.processing_ms)
            if frame.error or audio.status().error:
                raise RuntimeError(frame.error or audio.status().error)
            sleep(0.005)
        audio_snapshot, light_snapshot = audio.snapshot(), lights.snapshot()
        if not audio_snapshot or not audio_snapshot.beat or audio_snapshot.beat.state != "locked" or not peak:
            raise RuntimeError("Sem sincronismo ou sem estados luminosos na sessão.")
        audio.stop()
        wait_for(lambda: lights.snapshot().status == "waiting" and all(s.intensity == 0 for s in lights.snapshot().states))
        controls = replace(lights.controls(), manual=True, manual_pan=0.8, manual_tilt=0.3)
        lights.set_controls(controls)
        wait_for(lambda: lights.snapshot().status == "manual")
        manual = lights.snapshot()
        blackout_at = monotonic()
        lights.set_controls(replace(controls, blackout=True))
        wait_for(lambda: lights.snapshot().blackout and all(s.intensity == 0 for s in lights.snapshot().states))
        blackout_delay_ms = (monotonic() - blackout_at) * 1000
        lights.set_controls(replace(controls, blackout=True, config=replace(controls.config, light_effect="ambient")))
        wait_for(lambda: lights.snapshot().effect == "ambient")
        latched = lights.snapshot()
        lights.set_controls(replace(controls, blackout=False))
        wait_for(lambda: lights.snapshot().status == "manual")
        result = {
            "source": "synthetic_test_only", "physical_output": False,
            "audio": asdict(audio.status()),
            "continuity_errors": audio_snapshot.continuity_errors,
            "beat": {"bpm": audio_snapshot.beat.bpm, "state": audio_snapshot.beat.state},
            "lighting": asdict(light_snapshot), "observed_frames": sampled_frames,
            "observed_peak_intensity": peak, "observed_max_processing_ms": lighting_peak_ms,
            "manual_without_audio": manual.status == "manual" and any(s.intensity > 0 for s in manual.states),
            "blackout_command_observed_ms": blackout_delay_ms,
            "blackout_survived_effect_change": latched.blackout and all(s.intensity == 0 for s in latched.states),
        }
    finally:
        lights.stop()
        audio.stop()
    result["worker_stopped"] = not lights.running
    result["final_intensities_zero"] = all(s.intensity == 0 for s in lights.snapshot().states)
    print(json.dumps(result, ensure_ascii=False))
    return 1 if (result["audio"]["dropped_blocks"] or result["continuity_errors"] or
                 not result["manual_without_audio"] or not result["blackout_survived_effect_change"] or
                 not result["worker_stopped"] or not result["final_intensities_zero"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
