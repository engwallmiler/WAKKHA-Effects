"""A força do kick pode provar o retorno sem esperar a mixagem recuperar."""
from dataclasses import replace
import math
import pytest
from beatlight.contracts import KickEvent
from beatlight.music.drop import DropDetector
from test_drop_energy import descriptor, Scene


def trained(shift=0):
    detector=DropDetector()
    for db in [-20]*8+[-8,-40]:
        detector.learn(descriptor(db+shift))
    return detector


@pytest.mark.parametrize('shift',[0,-12,-24])
def test_peak_mean_is_robust_linear_power_and_immediately_proves_full_attack(shift):
    detector=trained(shift)
    assert detector.reference_peak_db==pytest.approx(-20+shift)
    attack=descriptor(-20+shift)
    assert detector.strong_candidate(KickEvent(10,10,.1,.95),attack,.5)
    # A média da mixagem ainda não recuperou e o kick não é um descritor early.
    assert not attack.early and attack.peak_low_db < -8+shift-4
    assert detector.recovered(attack,-30+shift,-30+shift,-8+shift,-32+shift)
    evidence=detector.snapshot(10,.5,5,True)
    assert evidence.mean_reached and evidence.peak_ratio==pytest.approx(1)
    assert evidence.reference_kicks==10


def test_loud_bass_peak_cannot_replace_transient_power_and_weak_roll_cannot_reach_mean():
    detector=trained()
    weak=replace(descriptor(-26),peak_low_db=-20)
    assert not detector.strong_candidate(KickEvent(10,10,1,.95),weak,.5)
    assert not detector.reaches_groove_mean(weak)
    assert not detector.recovered(weak,-30,-30,-8,-32)
    for at in (10.25,10.5,10.75):
        assert not detector.strong_candidate(KickEvent(at,at,1,.95),descriptor(-24),.5)
    assert detector.accelerated and not detector.mean_reached
    assert detector.strong_candidate(KickEvent(11,11,.1,.95),descriptor(-20),.5)
    assert detector.mean_reached


def test_dual_mean_has_small_tolerance_but_does_not_let_absolute_peak_replace_attack():
    detector=trained()
    within=replace(descriptor(-20+10*math.log10(.92)),peak_low_db=-20+10*math.log10(.88))
    assert detector.reaches_groove_mean(within)
    assert not detector.reaches_groove_mean(replace(within,power_db=-23))
    assert not detector.reaches_groove_mean(replace(within,peak_low_db=-23))


def test_groove_reference_freezes_through_build_and_first_real_return():
    scene=Scene();scene.segment(6,kicks=True)
    detector=scene.tracker._drop_detector
    original=(tuple(detector.powers),tuple(detector.peak_powers),detector.reference_db,detector.reference_peak_db)
    scene.segment(5,roll=True)
    scene.segment(2,kicks=True,amplitude=.55,interval=.25,roll=True)
    first=scene.segment(.24,kicks=True)
    assert any(s.state=='drop' and s.drop_kicks==1 for s in first)
    assert original==(tuple(detector.powers),tuple(detector.peak_powers),detector.reference_db,detector.reference_peak_db)


def test_peak_reference_is_not_ready_without_four_real_measured_peaks():
    detector=DropDetector()
    for _ in range(8):detector.learn(replace(descriptor(-20),peak_low_db=-120))
    assert detector.ready and detector.reference_peak_db is None
    assert not detector.reaches_groove_mean(descriptor(-20))
