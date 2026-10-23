import numpy as np
import pytest
from beatlight.audio.demo import structure_demo_samples
from beatlight.contracts import AudioBlock
from beatlight.dsp.pipeline import AudioAnalyzer


@pytest.mark.parametrize("offbeat", [True, False])
def test_bass_without_kick_is_not_a_drop_and_real_grid_return_still_is(offbeat):
    analyzer = AudioAnalyzer()
    false_section, true_section = [], []
    raw_events = set()
    for seq, first in enumerate(range(0, 48000 * 26, 512)):
        t = np.arange(first, first + 512) / 48000
        x = structure_demo_samples(t)
        # Baixo de ataque forte com hats, melodia e roll do demo, sem kick em 12–20 s.
        offset = 0.25 if offbeat else 0
        phase = (t - offset) % 0.5
        env = np.exp(-phase * (18 if offbeat else 1.5))
        bass = 0.65 * env * np.sin(2 * np.pi * (80 if offbeat else 110) * t)
        x += ((bass * ((t >= 12) & (t < 20)))[:, None]).astype(np.float32)
        x.setflags(write=False)
        at = 100 + first / 48000
        s = analyzer.process(AudioBlock("bass-test", x, 48000, 2, seq, 512, at, at + 512 / 48000))
        assert not s.structure_error
        if s.structure and 13 <= t[0] < 20:
            false_section.append(s.structure)
            raw_events.update(e.occurred_at for e in s.kicks.events if 112 <= e.occurred_at < 120)
        if s.structure and t[0] >= 20:
            true_section.append(s.structure)
    assert len(raw_events) >= 4, "O teste precisa provocar candidatos graves ambíguos"
    assert false_section and all(s.state != "drop" for s in false_section)
    assert false_section[-1].grid.rejected_offgrid + false_section[-1].rejected_timbre + false_section[-1].rejected_returns >= 4
    assert any(s.state == "drop" for s in true_section)
    first_drop = next(s for s in true_section if s.state == "drop")
    assert 119.97 <= first_drop.drop_at <= 121.2  # o baixo sustentado pode mascarar os primeiros ataques
    assert {s.drop_kicks for s in true_section if s.state == "drop"} == set(range(1, 9))
    assert true_section[-1].state == "groove"


def test_aggressive_harmonic_bass_on_the_grid_does_not_create_drop():
    analyzer = AudioAnalyzer()
    false_section, returned = [], []
    raw_times=set()
    for seq,first in enumerate(range(0,48000*26,512)):
        t=np.arange(first,first+512)/48000
        x=structure_demo_samples(t)
        bass=0.65*np.exp(-(t%0.5)*28)*np.tanh(12*np.sin(2*np.pi*70*t))
        x+=((bass*((t>=12)&(t<20)))[:,None]).astype(np.float32)
        x.setflags(write=False)
        at=100+first/48000
        snapshot=analyzer.process(AudioBlock("aggressive-bass",x,48000,2,seq,512,at,at+512/48000))
        assert not snapshot.structure_error and not snapshot.texture_error
        if snapshot.structure and 13<=t[0]<20:
            false_section.append(snapshot.structure)
            raw_times.update(e.occurred_at for e in snapshot.kicks.events if 112<=e.occurred_at<120)
        if snapshot.structure and t[0]>=20:
            returned.append(snapshot.structure)
    assert len(raw_times)>=6
    assert all(s.state!="drop" for s in false_section)
    assert analyzer._structure._identity.rejected_harmonics>=4
    assert any(s.state=="drop" for s in returned)
    assert {s.drop_kicks for s in returned if s.state=="drop"}==set(range(1,9))
