"""Diagnóstico Link independente: python -m beatlight.sync --seconds 15."""
import argparse
from dataclasses import asdict
import json
from time import monotonic, sleep
from beatlight.sync.link import LinkRuntime


def main():
    parser = argparse.ArgumentParser(description="Monitor Ableton Link: lê tempo/fase sem controlar transporte ou decks.")
    parser.add_argument("--seconds", type=float, default=15, help="Duração do diagnóstico (1 a 3600 s).")
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600:
        parser.error("Use duração entre 1 e 3600 s.")
    runtime = LinkRuntime()
    connected = False
    try:
        runtime.start()
        until = monotonic() + args.seconds
        while monotonic() < until:
            sleep(.2)
            state = runtime.snapshot()
            print(json.dumps(asdict(state), ensure_ascii=False), flush=True)
            connected |= state.usable(monotonic())
            if state.state == "error":
                return 2
            sleep(.8)
    except KeyboardInterrupt:
        pass
    finally:
        runtime.stop()
    return 0 if connected else 1


if __name__ == "__main__":
    raise SystemExit(main())
