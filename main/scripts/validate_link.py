"""Dois participantes nativos locais, sem alterar tempo ou transporte da sessão.

Pode ingressar em uma sessão Link já aberta. Não cria nem controla decks.
"""
from dataclasses import asdict
import json
from pathlib import Path
from time import monotonic, sleep
from beatlight.sync.link import LinkRuntime
from beatlight.sync.timeline import link_grid


def main():
    a, b = LinkRuntime(), LinkRuntime()
    errors, samples = [], []
    report = {}
    try:
        a.start()
        b.start()
        until = monotonic() + 12
        while monotonic() < until:
            sleep(.1)
            now = monotonic()
            sa, sb = a.snapshot(), b.snapshot()
            if sa.state == "error" or sb.state == "error":
                raise RuntimeError(sa.error or sb.error)
            ga, gb = link_grid(sa, now), link_grid(sb, now)
            if ga and gb:
                phase_error = ((ga.beat_index + ga.phase - gb.beat_index - gb.phase + 4) % 8) - 4
                errors.append(abs(phase_error * ga.period * 1000))
                samples.append((sa.tempo, sb.tempo, sa.peers, sb.peers))
                if len(errors) >= 25:
                    break
        assert len(errors) >= 25, "Não foram encontrados dois participantes Link nativos. Confira rede/firewall."
        assert max(errors[-15:]) < 20, errors
        assert all(abs(x - y) < .01 for x, y, _, _ in samples[-15:]), samples
        report = {"native": True, "samples": len(samples), "tempo": samples[-1][0],
            "peers": [samples[-1][2], samples[-1][3]],
            "max_phase_error_ms_settled": max(errors[-15:]),
            "last_a": asdict(a.snapshot()), "last_b": asdict(b.snapshot()),
            "tempo_or_transport_commands": 0, "initial_tempo_if_first": 120.0}
    finally:
        a.stop()
        b.stop()
    report["shutdown"] = [a.snapshot().state, b.snapshot().state]
    (Path(__file__).resolve().parents[1] / "docs" / "resultado-link-v0.17.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
