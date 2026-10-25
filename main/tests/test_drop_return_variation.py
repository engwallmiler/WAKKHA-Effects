"""Retornos com outra altura grave e ataques do build encostando no impacto."""
import numpy as np
import pytest
from beatlight.contracts import AudioBlock
from beatlight.dsp.pipeline import AudioAnalyzer
from test_drop_first_attack import track
from test_drop_energy import Scene


def test_long_weak_kick_section_cannot_relearn_itself_as_full_groove_and_disarm_return():
    scene=Scene();scene.segment(6,kicks=True)
    reference=scene.tracker._drop_detector.reference_db
    scene.segment(3,kicks=True,amplitude=.55,interval=.25)
    scene.segment(1,kicks=True,amplitude=.55,interval=.25,roll=True)
    returned=scene.segment(.24,kicks=True)
    drop=next((s for s in returned if s.state=='drop'),None)
    assert drop and drop.drop_at==pytest.approx(10)
    assert drop.updated_at-10<.13
    assert drop.drop_evidence.reference_db==pytest.approx(reference,abs=.1)


@pytest.mark.parametrize('gain',[.55,.25])
def test_normal_tempo_volume_change_keeps_groove_instead_of_looking_like_kick_withdrawal(gain):
    scene=Scene();scene.segment(6,kicks=True)
    frames=scene.segment(6,kicks=True,amplitude=gain)
    assert all(s.state=='groove' and s.drop_id==0 for s in frames)


@pytest.mark.parametrize('variation',[{'pitch':1.28},{'pitch':1.40},{'roll':True}])
def test_first_impact_survives_timbre_shift_or_general_detector_refractory(variation):
    analyzer=AudioAnalyzer()
    first_drop=None
    for seq,first in enumerate(range(0,48000*13,512)):
        t=np.arange(first,first+512)/48000
        x=track(t,**({} if variation.get('roll') else variation))
        if variation.get('roll'):
            phase=(t-.125)%.25
            env=np.exp(-phase*24)*((t>=9)&(t<12))
            x[:,0]+=(.45*.65*env*np.sin(2*np.pi*70*t)).astype(np.float32)
            x[:,1]+=(.40*.65*env*np.sin(2*np.pi*85*t)).astype(np.float32)
        x.setflags(write=False)
        at=100+first/48000
        result=analyzer.process(AudioBlock('return-variation',x,48000,2,seq,512,at,at+512/48000))
        assert not result.structure_error and not result.kick_error
        if result.structure and result.structure.state=='drop':
            assert first>=48000*12,'Promoveu kick fraco do build a drop'
            first_drop=result.structure
            assert at+512/48000-112<.11
            break
    assert first_drop and first_drop.drop_at==pytest.approx(112,abs=.055)


def test_pitched_slow_bass_with_hats_remains_rejected_despite_spectral_shift_tolerance():
    analyzer=AudioAnalyzer()
    for seq,first in enumerate(range(0,48000*14,512)):
        t=np.arange(first,first+512)/48000
        x=track(t,gain=0)
        env=np.exp(-(t%.5)*8)*(t>=12)
        x[:,0]+=(.6*env*np.sin(2*np.pi*98*t)).astype(np.float32)
        x[:,1]+=(.6*env*np.sin(2*np.pi*119*t)).astype(np.float32)
        x.setflags(write=False)
        at=100+first/48000
        result=analyzer.process(AudioBlock('bass-pitched',x,48000,2,seq,512,at,at+512/48000))
        assert not result.structure_error
        assert result.structure is None or result.structure.drop_id==0
