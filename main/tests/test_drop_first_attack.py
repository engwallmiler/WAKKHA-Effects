"""O primeiro impacto deve chegar à saída do pipeline, sem esperar outro kick."""
import numpy as np
import pytest
from dataclasses import replace

from beatlight.contracts import AudioBlock
from beatlight.dsp.pipeline import AudioAnalyzer
from beatlight.music.grid import grid_clock
from beatlight.sync.link import LinkSnapshot
from beatlight.sync.timeline import link_grid


def track(t, *, tail=24, pitch=1, gain=1, pause=0, bass=False, crash=False, shift=0,
          bass_level=.20, bass_from=8):
    groove = t < 6
    returned = t >= 12+shift
    phase = np.where(returned,(t-shift) % .5,t % .5)
    envelope = np.exp(-phase * np.where(returned, tail, 24))
    level = np.where(returned, gain, 1) * (groove | returned)
    frequencies = np.where(returned, pitch, 1)
    left = .45 * envelope * level * np.sin(2*np.pi*70*frequencies*t)
    right = .40 * envelope * level * np.sin(2*np.pi*85*frequencies*t)
    melody = .05 * (np.sin(2*np.pi*440*t)+np.sin(2*np.pi*660*t))
    roll = (t >= 9) & (t < 12)
    roll_phase = (t-9)*4+(t-9)**2
    snare = .12*roll*np.exp(-(roll_phase % 1)*18)*np.sin(2*np.pi*1100*t)
    hats = .025*np.exp(-((t*4) % 1)*15)*np.sin(2*np.pi*6500*t)
    if bass:
        # O baixo continua pelo impacto: não há recuperação de 7 dB na média.
        bed = bass_level * (t >= bass_from) * np.sin(2*np.pi*105*t)
        left += bed
        right += bed
    if crash:
        snare += .20*returned*np.exp(-np.maximum(0,t-12)*3)*(
            np.sin(2*np.pi*800*t)+np.sin(2*np.pi*3700*t))
    x = np.column_stack((left+melody+snare+hats,right+melody+snare+hats)).astype(np.float32)
    if pause:
        x[(t >= 12-pause) & (t < 12)] = 0
    return x


CASES = [
    {}, {"pause": .125}, {"pause": .5}, {"tail": 18},
    {"tail": 36}, {"pitch": .90}, {"pitch": 1.12},
    {"gain": .87}, {"bass": True}, {"crash": True},
    {"bass":True,"bass_level":.30,"bass_from":6},
]


@pytest.mark.parametrize("variation", CASES, ids=lambda v: str(v))
def test_first_attack_emitted_without_waiting_for_second_kick(variation):
    analyzer = AudioAnalyzer()
    first_drop = None
    for seq, first in enumerate(range(0, 48000*13, 512)):
        t = np.arange(first,first+512)/48000
        x = track(t, **variation)
        x.setflags(write=False)
        at = 100 + first/48000
        result = analyzer.process(AudioBlock("first-attack",x,48000,2,seq,512,at,at+512/48000))
        assert not result.structure_error and not result.kick_error
        if result.structure and result.structure.state == "drop":
            assert first >= 48000*12, "Antecipou o drop durante o build"
            first_drop = (result.structure, at+512/48000)
            break
    assert first_drop, "Nenhum drop detectado no primeiro segundo do retorno"
    detected, emitted_at = first_drop
    assert detected.drop_at == pytest.approx(112, abs=.055)
    assert detected.drop_kicks == 1
    # Inclui janela FFT, cauda de confirmação e entrega do bloco, não só timestamp retroativo.
    assert emitted_at-112 < .10


def shifted_clock(at):
    shift = .16 if at>=111 else 0
    return grid_clock(link_grid(LinkSnapshot(at,"connected",120,(at-100-shift)*2,1,1),at),at)


def test_link_phase_validates_first_impact_without_four_kick_local_realignment():
    analyzer = AudioAnalyzer(clock_provider=shifted_clock)
    for seq,first in enumerate(range(0,48000*13,512)):
        t=np.arange(first,first+512)/48000
        x=track(t,shift=.16)
        x.setflags(write=False)
        at=100+first/48000
        snapshot=analyzer.process(AudioBlock("shifted-link",x,48000,2,seq,512,at,at+512/48000))
        assert not snapshot.structure_error
        if snapshot.structure and snapshot.structure.state=="drop":
            assert snapshot.structure.drop_at==pytest.approx(112.16,abs=.055)
            assert at+512/48000-112.16<.10
            assert snapshot.structure.grid.corrections==0  # primeiro ataque não corrige a grade local
            break
    else:
        pytest.fail("Link alinhado não deve esperar quatro kicks na grade local antiga")


@pytest.mark.parametrize("release_late",[False,True])
def test_missing_general_detection_is_recovered_once_and_keeps_eight_real_kicks(monkeypatch,release_late):
    analyzer=AudioAnalyzer()
    original=analyzer._kicks.push
    def hide_first(block):
        result=original(block)
        if result and (not release_late or block.acquired_at<112.10):
            events=tuple(e for e in result.events if not 111.95<e.occurred_at<112.05)
            return replace(result,events=events,last_event=events[-1] if events else None)
        return result
    monkeypatch.setattr(analyzer._kicks,"push",hide_first)
    drops=[]
    first_emitted=None
    for seq,first in enumerate(range(0,48000*17,512)):
        t=np.arange(first,first+512)/48000
        x=track(t)
        x.setflags(write=False)
        at=100+first/48000
        snapshot=analyzer.process(AudioBlock("recovered",x,48000,2,seq,512,at,at+512/48000))
        assert not snapshot.structure_error and not snapshot.kick_error
        if snapshot.structure and snapshot.structure.state=="drop":
            if first_emitted is None:
                first_emitted=at+512/48000
            drops.append(snapshot.structure)
    assert drops and first_emitted-112<.10
    assert drops[0].drop_at==pytest.approx(112,abs=.055)
    assert drops[0].drop_evidence.rescued_attack
    assert {s.drop_kicks for s in drops}==set(range(1,9))
    assert {s.drop_id for s in drops}=={1}
    assert snapshot.structure.state=="groove"


@pytest.mark.parametrize("variation",[{"gain":0,"crash":True},{"gain":0,"bass":True}])
def test_link_and_returning_highs_or_continuous_bass_cannot_invent_kick(variation):
    analyzer=AudioAnalyzer(clock_provider=shifted_clock)
    for seq,first in enumerate(range(0,48000*13,512)):
        t=np.arange(first,first+512)/48000
        x=track(t,**variation)
        x.setflags(write=False)
        at=100+first/48000
        snapshot=analyzer.process(AudioBlock("no-impact",x,48000,2,seq,512,at,at+512/48000))
        assert not snapshot.structure_error
        assert snapshot.structure is None or snapshot.structure.drop_id==0


@pytest.mark.parametrize("rate,bpm,gain,channels",[(44100,128,.25,1),(48000,96,1,2),(48000,150,.25,2)])
def test_first_return_across_tempo_capture_rate_gain_and_channels(rate,bpm,gain,channels):
    analyzer=AudioAnalyzer()
    drop_time=12*120/bpm
    for seq,first in enumerate(range(0,int(rate*(drop_time+1)),512)):
        t=np.arange(first,first+512)/rate
        x=(track(t*bpm/120,crash=True)*gain).astype(np.float32)
        if channels==1:
            x=x[:,:1].copy()
        x.setflags(write=False)
        at=100+first/rate
        snapshot=analyzer.process(AudioBlock("different-tempo",x,rate,channels,seq,512,at,at+512/rate))
        assert not snapshot.structure_error and not snapshot.kick_error
        if snapshot.structure and snapshot.structure.state=="drop":
            assert snapshot.structure.drop_at==pytest.approx(100+drop_time,abs=.055)
            assert at+512/rate-(100+drop_time)<.10
            break
    else:
        pytest.fail("Primeiro kick não foi reconhecido")


@pytest.mark.parametrize("variation",[{"shift":.075},{"bass":True,"bass_level":.30,"bass_from":6}])
def test_forecast_drift_or_dense_bass_keeps_first_impact_and_all_eight_kicks(variation):
    analyzer=AudioAnalyzer()
    drops=[]
    first_emitted=None
    for seq,first in enumerate(range(0,48000*17,512)):
        t=np.arange(first,first+512)/48000
        x=track(t,**variation)
        x.setflags(write=False)
        at=100+first/48000
        snapshot=analyzer.process(AudioBlock("forecast-drift",x,48000,2,seq,512,at,at+512/48000))
        assert not snapshot.structure_error
        if snapshot.structure and snapshot.structure.state=="drop":
            if first_emitted is None:
                first_emitted=at+512/48000
            drops.append(snapshot.structure)
    expected=112+variation.get("shift",0)
    assert drops and drops[0].drop_at==pytest.approx(expected,abs=.055)
    assert first_emitted-expected<.10
    assert drops[0].grid.corrections==0
    assert {s.drop_kicks for s in drops}==set(range(1,9))
    assert snapshot.structure.state=="groove"


def test_harmonic_bass_with_simultaneous_crash_is_still_not_a_kick():
    analyzer=AudioAnalyzer()
    for seq,first in enumerate(range(0,48000*14,512)):
        t=np.arange(first,first+512)/48000
        x=track(t,gain=0,crash=True)
        bass=.65*np.exp(-(t%.5)*28)*np.tanh(12*np.sin(2*np.pi*70*t))*(t>=12)
        x+=bass[:,None].astype(np.float32)
        x.setflags(write=False)
        at=100+first/48000
        snapshot=analyzer.process(AudioBlock("bass-and-crash",x,48000,2,seq,512,at,at+512/48000))
        assert not snapshot.structure_error
        assert snapshot.structure is None or snapshot.structure.drop_id==0
