from beatlight.contracts import FixtureDefinition


def default_fixtures() -> tuple[FixtureDefinition, ...]:
    """Inventário de demonstração; não descreve aparelhos físicos conectados."""
    return tuple(FixtureDefinition(f"par-{i + 1}", f"PAR {i + 1:02d}", "par",
        ("wash", "A" if i % 2 == 0 else "B"), ("intensity", "rgb", "white")) for i in range(4)) + tuple(
        FixtureDefinition(f"move-{i + 1}", f"MOV {i + 1:02d}", "moving_head",
            ("movers", "A" if i % 2 == 0 else "B"), ("intensity", "rgb", "white", "pan", "tilt")) for i in range(2))
