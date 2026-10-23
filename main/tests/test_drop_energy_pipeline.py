"""Áudio completo: roll com kick dobrado fraco, pausa e primeiro impacto real."""
import numpy as np
import pytest
from beatlight.audio.demo import structure_demo_samples
from beatlight.contracts import AudioBlock
from beatlight.dsp.pipeline import AudioAnalyzer
from beatlight.sync.link import LinkSnapshot
from beatlight.sync.timeline import link_grid
from beatlight.music.grid import grid_clock


def composition(t, *, pause=True, weak=True):
    x = structure_demo_samples(t)
    if weak:
        # Mesmo kick/cauda do groove; amplitude menor e frequência de repetição dupla.
        build = (t >= 12) & (t < 19.5)
        env = np.exp(-((t*4) % 1)*6) * build
        x[:,0] += (.45*.55*env*np.sin(2*np.pi*70*t)).astype(np.float32)
        x[:,1] += (.40*.55*env*np.sin(2*np.pi*85*t)).astype(np.float32)
    if pause:
        x[(t >= 19.5) & (t < 20)] = 0
    return x


@pytest.mark.parametrize("gain,link", [(1.0,False),(.25,False),(1.0,True),(.25,True)])
def test_weak_double_build_then_short_silence_detects_first_full_kick(gain,link):
    def clock(at):
        sample = LinkSnapshot(at, "connected", 120, (at-100)*2, 1, 1)
        return grid_clock(link_grid(sample, at), at)
    analyzer = AudioAnalyzer(clock_provider=clock if link else None)
    build, silent, drops = [], [], []
    raw_weak = set()
    for seq,first in enumerate(range(0,48000*25,512)):
        t = np.arange(first,first+512)/48000
        x = (composition(t)*gain).astype(np.float32)
        x.setflags(write=False)
        at = 100 + first/48000
        snapshot = analyzer.process(AudioBlock("drop-energy",x,48000,2,seq,512,at,at+512/48000))
        assert not snapshot.structure_error and not snapshot.kick_error
        s = snapshot.structure
        if not s:
            continue
        if 112 <= s.updated_at < 119.5:
            build.append(s)
            raw_weak.update(e.occurred_at for e in snapshot.kicks.events if 112 <= e.occurred_at < 119.5)
        if 119.9 <= s.updated_at < 119.98:
            silent.append(s)
        if s.state == "drop":
            drops.append(s)
    assert len(raw_weak)>=8  # realmente houve detecções graves no build
    assert all(s.state!="drop" for s in build)
    assert max(s.drop_evidence.rejected_weak for s in build)>=2
    assert silent and all(s.state=="silence" and s.reference_ready for s in silent)
    assert drops and drops[0].drop_kicks==1
    assert drops[0].drop_at == pytest.approx(120, abs=.055)
    assert drops[0].updated_at-120 < .18
    assert {s.drop_kicks for s in drops} == set(range(1,9))
    assert snapshot.structure.state == "groove"
    assert snapshot.continuity_errors==0
