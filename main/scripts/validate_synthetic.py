"""Sessão sintética com entrega em tempo real; não usa nem reproduz áudio real."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from time import monotonic, sleep
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from beatlight.audio.synthetic import SyntheticSource
from beatlight.core.runtime import CaptureRuntime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=12)
    args = parser.parse_args()
    if not np.isfinite(args.seconds) or args.seconds < 1:
        parser.error("Use uma duração finita de pelo menos 1 segundo.")
    runtime = CaptureRuntime()
    source = SyntheticSource()
    samples = []
    previous_sequence = -1
    try:
        runtime.start(source, source.devices()[0], 512)
        deadline = monotonic() + args.seconds
        while monotonic() < deadline and runtime.status().state == "running":
            snapshot = runtime.snapshot()
            if snapshot and snapshot.sequence != previous_sequence:
                samples.append(snapshot.processing_ms)
                previous_sequence = snapshot.sequence
            sleep(0.005)
    finally:
        runtime.stop()
    status, snapshot = runtime.status(), runtime.snapshot()
    kicks = snapshot.kicks if snapshot else None
    beat = snapshot.beat if snapshot else None
    result = {
        "source": "synthetic_test_only", "status": asdict(status),
        "continuity_errors": snapshot.continuity_errors if snapshot else None,
        "analysis_error": snapshot.analysis_error if snapshot else "no snapshots",
        "kick_error": snapshot.kick_error if snapshot else "no snapshots",
        "kicks": {"count": kicks.count, "ready": kicks.ready, "retained_events": len(kicks.events),
                  "history_points": len(kicks.history)} if kicks else None,
        "beat": {"bpm": beat.bpm, "state": beat.state, "confidence": beat.confidence,
                 "phase_error_ms": beat.phase_error_ms, "matched_kicks": beat.matched_kicks,
                 "history_points": len(beat.history)} if beat else None,
        "beat_error": snapshot.beat_error if snapshot else "no snapshots",
        "processing_sample_count": len(samples),
        "processing_ms": {"mean": float(np.mean(samples)), "p95": float(np.percentile(samples, 95)),
                          "max": float(np.max(samples))} if samples else None,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 1 if (status.error or not snapshot or snapshot.analysis_error or snapshot.kick_error
                 or snapshot.beat_error or not beat or beat.state != "locked"
                 or not kicks or not kicks.count or status.dropped_blocks or snapshot.continuity_errors) else 0


if __name__ == "__main__":
    raise SystemExit(main())
