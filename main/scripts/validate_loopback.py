"""Inspeção real sem gravar áudio nem gerar reprodução sonora.

Selecione explicitamente a saída, quando necessário:
python scripts/validate_loopback.py --device Realtek --seconds 10 --cycles 3
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from time import monotonic, sleep
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from beatlight.audio.wasapi import WasapiSource
from beatlight.core.runtime import CaptureRuntime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="", help="Parte do nome da saída")
    parser.add_argument("--seconds", type=float, default=3)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--all-devices", action="store_true")
    args = parser.parse_args()
    devices = WasapiSource().devices()
    print(json.dumps({"devices": [asdict(d) for d in devices]}, ensure_ascii=False))
    eligible = [d for d in devices if args.device.casefold() in d.name.casefold()]
    if not eligible:
        raise SystemExit("Nenhuma saída corresponde ao filtro.")
    selected = eligible if args.all_devices else [next((d for d in eligible if d.is_default), eligible[0])]
    runtime = CaptureRuntime()
    failed = False
    inconclusive = False
    for device in selected:
        for cycle in range(args.cycles):
            try:
                runtime.start(WasapiSource(), device, 512)
                deadline = monotonic() + max(0.1, args.seconds)
                while monotonic() < deadline and runtime.status().state == "running":
                    sleep(0.05)
            except Exception as exc:
                print(json.dumps({"error": str(exc)}, ensure_ascii=False))
            finally:
                runtime.stop()
            status = runtime.status()
            snapshot = runtime.snapshot()
            failed = failed or bool(status.error) or bool(snapshot and (snapshot.analysis_error or snapshot.kick_error or snapshot.beat_error))
            inconclusive = inconclusive or not status.blocks
            print(json.dumps({"device": device.name, "cycle": cycle + 1,
                "validation": "blocks_received" if status.blocks else "inconclusive_no_playback",
                "status": asdict(status),
                "spectral": {"frame_id": snapshot.spectral.frame_id,
                "fft_size": snapshot.spectral.fft_size, "hop_size": snapshot.spectral.hop_size,
                "rms_db": snapshot.spectral.total_rms_db,
                "dominant_hz": snapshot.spectral.dominant_hz,
                "band_levels_db": snapshot.spectral.band_levels_db,
                "transient_count": snapshot.spectral.transient_count} if snapshot and snapshot.spectral else None,
                "kicks": {"count": snapshot.kicks.count, "band_db": snapshot.kicks.band_db,
                "score": snapshot.kicks.score, "threshold": snapshot.kicks.threshold,
                "ready": snapshot.kicks.ready} if snapshot and snapshot.kicks else None,
                "beat": {"bpm": snapshot.beat.bpm, "state": snapshot.beat.state,
                "confidence": snapshot.beat.confidence, "phase_error_ms": snapshot.beat.phase_error_ms}
                if snapshot and snapshot.beat else None,
                "beat_error": snapshot.beat_error if snapshot else "",
                "kick_error": snapshot.kick_error if snapshot else "",
                "analysis_error": snapshot.analysis_error if snapshot else "", "meter": {"rms_db": snapshot.rms_db,
                "peak_db": snapshot.peak_db, "silent": snapshot.silent,
                "processing_ms": snapshot.processing_ms,
                "continuity_errors": snapshot.continuity_errors} if snapshot else None},
                ensure_ascii=False))
    return 1 if failed else 2 if inconclusive else 0


if __name__ == "__main__":
    raise SystemExit(main())
