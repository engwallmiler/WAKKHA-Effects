"""Ataques de baixo podem passar a triagem normal sem autorizar o drop."""
from dataclasses import replace
import numpy as np
import pytest
from beatlight.contracts import KickEvent,StructureFeatures,AudioBlock
from beatlight.music.kick_identity import KickIdentity
from beatlight.music.structure import StructureTracker
from beatlight.audio.demo import structure_demo_samples
from beatlight.dsp.pipeline import AudioAnalyzer
from test_kick_identity import trained_identity,SHAPE


def weak_attack(gate, *, shape=SHAPE,decay=40,harmonics=-120):
    event=KickEvent(105,105.02,.8,.9)
    normal=[]
    strict=[]
    for i in range(18):
        age=i/100
        f=StructureFeatures(i,105+age,-15-decay*age,-35,-12,.2,False,
            low_shape=shape,harmonic_db=harmonics-decay*age)
        for e in gate.push(f,(event,)):
            normal.append(e)
            strict.append(gate.return_matches(e))
            gate.discard(e)
    return normal,strict


@pytest.mark.parametrize("fields",[
    dict(decay=40),
    dict(shape=(0,.4,.9165,0),decay=100),
    dict(decay=100,harmonics=-30.5),
])
def test_normal_candidate_cannot_authorize_drop_when_identity_is_ambiguous(fields):
    normal,strict=weak_attack(trained_identity(),**fields)
    assert len(normal)==1 and strict==[False]


def test_learned_kick_has_strict_return_evidence():
    normal,strict=weak_attack(trained_identity(),decay=100)
    assert len(normal)==1 and strict==[True]


def test_structure_blocks_loose_return_and_preserves_breakdown_context(monkeypatch):
    from test_structure import Performance
    p=Performance()
    p.groove()
    p.segment(3,low=-70,rms=-25,kicks=False)
    monkeypatch.setattr(p.structure._identity,"return_matches",lambda event:False)
    frames=p.segment(3,kicks=True,low=-20)
    assert all(s.state!="drop" and s.drop_id==0 for s in frames)
    assert frames[-1].rejected_returns>=4 and frames[-1].state=="breakdown"


@pytest.mark.parametrize("gain",[1.0,.25])
def test_audio_path_bass_plucks_on_grid_do_not_create_drop(gain):
    analyzer=AudioAnalyzer()
    states=[]
    blocked=0
    for seq,first in enumerate(range(0,48000*12,512)):
        t=np.arange(first,first+512)/48000
        if first<48000*6:
            x=structure_demo_samples(t)
        else:
            x=np.column_stack((.02*np.sin(2*np.pi*440*t),.02*np.sin(2*np.pi*660*t)))
            if first>=48000*9:
                phase=t%.5
                env=np.exp(-phase*8)
                x[:,0]+=.45*env*np.sin(2*np.pi*70*t)
                x[:,1]+=.4*env*np.sin(2*np.pi*85*t)
            x=x.astype(np.float32)
        x=(x*gain).astype(np.float32)
        x.setflags(write=False)
        at=100+first/48000
        s=analyzer.process(AudioBlock("bass-return",x,48000,2,seq,512,at,at+512/48000))
        assert not s.structure_error and not s.kick_error
        if first>=48000*9 and s.structure:
            states.append(s.structure.state)
            blocked=max(blocked,s.structure.rejected_returns)
    assert "drop" not in states and blocked>=2


def test_loose_bass_candidate_cannot_rewrite_the_learned_kick_profile():
    from test_kick_identity import attack
    gate=trained_identity()
    before=tuple(gate.references)
    assert len(attack(gate,105,decay=40,learn=True))==1
    assert tuple(gate.references)==before


def test_true_kick_variation_can_still_update_the_reference():
    from test_kick_identity import attack
    gate=trained_identity()
    before=len(gate.references)
    assert len(attack(gate,105,decay=80,learn=True))==1
    assert len(gate.references)==before+1
