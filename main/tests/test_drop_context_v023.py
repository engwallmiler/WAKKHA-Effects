import math
import numpy as np
import pytest
from beatlight.contracts import AudioBlock,KickEvent,StructureFeatures
from beatlight.dsp.pipeline import AudioAnalyzer
from beatlight.dsp.structure_features import StructureFeatureExtractor
from beatlight.music.drop import DropDetector
from test_drop_energy import descriptor
from test_drop_first_attack import track
from test_structure import Performance


def test_novel_spectral_attack_reinforces_a_real_kick_without_a_crash_but_not_a_weak_roll():
    d=DropDetector()
    for _ in range(8):d.learn(descriptor(-20,high=-20))
    returning=descriptor(-20+10*math.log10(.78),high=-45)
    assert not d.strong_candidate(KickEvent(10,10,.5,.95),returning,.5)
    f=StructureFeatures(1,10.5,-18,-45,-20,.2,True,spectral_flux=.4,spectral_novelty=.7)
    d.observe(f,True,.5)
    assert d.strong_candidate(KickEvent(10.5,10.5,.5,.95),returning,.5)
    for at in (10.75,11,11.25):
        result=d.strong_candidate(KickEvent(at,at,.5,.95),returning,.5)
    assert d.accelerated and not result
    events=[KickEvent(12+i*.25,12+i*.25,.8,.9) for i in range(16)]
    sequential,batch=DropDetector(),DropDetector()
    for event in events:sequential.observe_candidate(event,.5)
    batch.observe_candidates(events,.5,16)
    batch.observe_candidates(events,.5,16.01)
    assert list(batch.candidate_times)==list(sequential.candidate_times) and batch.accelerated==sequential.accelerated


def test_first_impact_is_immediate_but_a_single_kick_cannot_latch_a_full_drop():
    p=Performance();p.groove();p.segment(6,kicks=False,low=-70,rms=-25)
    first=p.segment(.02)
    assert first[0].state=='drop' and first[0].drop_evidence.phase=='impact'
    after=p.segment(2,kicks=False,low=-70,rms=-25)
    assert after[-1].state!='drop' and after[-1].drop_kicks==0
    assert after[-1].drop_evidence.rejected_impacts==1


def test_continuity_confirmation_does_not_delay_the_first_impact_or_shorten_eight_kicks():
    p=Performance();p.groove();p.segment(6,kicks=False,low=-70,rms=-25)
    returned=p.segment(4.5)
    drops=[s for s in returned if s.state=='drop']
    assert drops[0].drop_kicks==1 and drops[0].drop_evidence.phase=='impact'
    assert any(s.drop_evidence.phase=='confirmed' and s.drop_kicks==3 for s in drops)
    assert {s.drop_kicks for s in drops}==set(range(1,9))


def test_kick_withdrawal_is_context_even_when_bass_remains_loud_and_no_roll_exists():
    analyzer=AudioAnalyzer();first_drop=None;broken=False
    for seq,first in enumerate(range(0,48000*13,512)):
        t=np.arange(first,first+512)/48000
        x=track(t,bass=True,bass_level=.35,bass_from=6)
        roll=(t>=9)&(t<12);phase=(t-9)*4+(t-9)**2
        x-=(.12*roll*np.exp(-(phase%1)*18)*np.sin(2*np.pi*1100*t))[:,None].astype(np.float32)
        x.setflags(write=False);at=100+first/48000
        result=analyzer.process(AudioBlock('bass-withdrawal',x,48000,2,seq,512,at,at+512/48000))
        assert not result.structure_error
        s=result.structure
        if s and 110<at<112:broken |= s.state in ('breakdown','buildup') or s.drop_evidence.armed
        if s and s.state=='drop':first_drop=at+512/48000;break
    assert broken,'Sem roll, graves sustentados não podem esconder oito tempos sem kick'
    assert first_drop is not None and first_drop-112<.13


def test_spectral_novelty_is_gain_invariant_but_detects_a_timbral_change():
    def extract(changed):
        extractor=StructureFeatureExtractor();features=[]
        for seq,first in enumerate(range(0,48000*3,512)):
            t=np.arange(first,first+512)/48000
            freq=np.where(t<2,440,6500 if changed else 440)
            gain=np.where(t<2,.1,.2)
            x=(gain*np.sin(2*np.pi*freq*t)).astype(np.float32)[:,None];x.setflags(write=False)
            features+=extractor.push(AudioBlock('novelty',x,48000,1,seq,512,first/48000,(first+512)/48000))
        return features
    same=extract(False);changed=extract(True)
    assert max(f.spectral_novelty for f in same if 2.2<f.at<2.4)<.05
    assert max(f.spectral_novelty for f in changed if 2<f.at<2.2)>.5
    assert all(0<=f.spectral_flux<=1 and 0<=f.spectral_novelty<=1 for f in changed)
