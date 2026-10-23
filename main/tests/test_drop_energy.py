"""Retorno no primeiro kick forte; rolls fracos não são antecipação do drop."""
from collections import deque
import math
import pytest
from beatlight.contracts import KickEvent, StructureFeatures
from beatlight.music.drop import DropDetector
from beatlight.music.kick_identity import Fingerprint
from beatlight.music.structure import StructureTracker

SHAPE = (0.0, .8, .6, 0.0)


def descriptor(db, high=-30):
    return Fingerprint(SHAPE, 10, 0, 15, db, db, high)


def test_reference_is_mean_linear_power_and_ignores_isolated_accents():
    detector = DropDetector()
    for db in [-20] * 8 + [-8, -40]:
        detector.learn(descriptor(db))
    assert detector.reference_db == pytest.approx(-20)
    assert detector.ready
    mixed = DropDetector()
    for db in [-20, -20, -14, -14]:
        mixed.learn(descriptor(db))
    expected = 10*math.log10((2*10**(-2)+2*10**(-1.4))/4)
    assert mixed.reference_db == pytest.approx(expected)
    assert mixed.reference_db != pytest.approx(-17)  # não faz média em dB


@pytest.mark.parametrize("shift", [0, -12, -24])
def test_weak_kick_is_compared_by_measured_power_not_normalized_intensity(shift):
    detector = DropDetector()
    for _ in range(8):
        detector.learn(descriptor(-20+shift))
    # A intensidade do evento é 100%, mas a potência real é só 25% da referência.
    assert not detector.strong_candidate(KickEvent(10, 10, 1, .95), descriptor(-26+shift), .5)
    assert detector.power_ratio == pytest.approx(10 ** (-.6))
    # Um kick forte pode chegar com intensidade normalizada pequena.
    assert detector.strong_candidate(KickEvent(10.5, 10.5, .05, .95), descriptor(-20+shift), .5)
    assert detector.power_ratio == pytest.approx(1)


def test_accelerated_weak_roll_does_not_block_the_first_full_strength_return():
    detector = DropDetector()
    for _ in range(8):
        detector.learn(descriptor(-20))
    for t in [10, 10.25, 10.5, 10.75]:
        assert not detector.strong_candidate(KickEvent(t,t,1,.9), descriptor(-24), .5)
    assert detector.accelerated and detector.rejected_weak == 4
    assert detector.strong_candidate(KickEvent(11,11,.1,.9), descriptor(-20), .5)
    assert detector.reference_db == pytest.approx(-20)


class Scene:
    def __init__(self):
        self.tracker = StructureTracker()
        self.events = deque(maxlen=16)
        self.at = 0.0
        self.frame = 0
        self.kick_at = -math.inf
        self.power_db = -15

    def segment(self, seconds, *, kicks=False, amplitude=1, interval=.5, roll=False, silent=False):
        result = []
        until = self.at + seconds
        next_kick = math.ceil((self.at-1e-6)/interval)*interval
        while self.at < until-1e-7:
            at = round(self.at, 8)
            if kicks and at >= next_kick-1e-7:
                self.kick_at = at
                self.power_db = -15 + 20*math.log10(amplitude)
                # O valor normalizado não é proporcional ao ganho da fixture.
                self.events.append(KickEvent(at, at+.02, 1 if amplitude<1 else .1, .95))
                next_kick += interval
            age = at-self.kick_at
            low = max(-90, self.power_db - 100*age)
            onset = self.frame % (12 if roll else 50) == 0
            feature = StructureFeatures(self.frame, at, -120 if silent else low,
                -120 if silent else -25 if roll else -38,
                -120 if silent else -20 if roll or kicks else -30,
                .3, onset and not silent, onset and roll and not silent,
                -25 if roll else -45, SHAPE, -100)
            result.append(self.tracker.process(feature, tuple(self.events)))
            self.frame += 1
            self.at = round(self.at+.01, 8)
        return result


def prepared_scene():
    scene = Scene()
    groove = scene.segment(6, kicks=True)
    assert groove[-1].reference_ready
    scene.segment(5, roll=True)
    assert scene.tracker._state == "buildup"
    return scene


@pytest.mark.parametrize("amplitude", [.4, .7, .8])
def test_half_beat_weak_kicks_keep_build_and_first_strong_kick_starts_drop(amplitude):
    scene = prepared_scene()
    before = scene.tracker._drop_detector.reference_db
    weak = scene.segment(3, kicks=True, amplitude=amplitude, interval=.25, roll=True)
    assert all(s.state != "drop" for s in weak)
    assert weak[-1].drop_evidence.rejected_weak >= 8
    assert weak[-1].grid.period == pytest.approx(.5)
    assert scene.tracker._drop_detector.reference_db == before
    start = scene.at
    returned = scene.segment(4.6, kicks=True)
    drop = next(s for s in returned if s.state == "drop")
    assert drop.drop_at == pytest.approx(start)
    assert drop.updated_at-start <= .12
    assert drop.drop_kicks == 1
    assert {s.drop_kicks for s in returned if s.state == "drop"} == set(range(1,9))
    assert returned[-1].state == "groove"


def test_half_second_silence_preserves_profile_but_lights_state_is_silent():
    scene = prepared_scene()
    quiet = scene.segment(.5, silent=True)
    assert quiet[-1].state == "silence" and quiet[-1].reference_ready
    assert quiet[-1].drop_evidence.pause_recent
    reference = quiet[-1].drop_evidence.reference_db
    start = scene.at
    returned = scene.segment(.2, kicks=True)
    first = next(s for s in returned if s.state == "drop")
    assert first.updated_at-start <= .12 and first.drop_kicks == 1
    assert first.drop_evidence.reference_db == reference


def test_long_stop_clears_the_preserved_reference_and_does_not_create_drop():
    scene = prepared_scene()
    stopped = scene.segment(2, silent=True)
    assert stopped[-1].state == "silence" and not stopped[-1].reference_ready
    assert stopped[-1].drop_evidence.reference_db is None
    restarted = scene.segment(3, kicks=True)
    assert all(s.state != "drop" for s in restarted)


def test_eight_missing_beats_arm_context_without_inventing_a_drop():
    scene = prepared_scene()
    frames = scene.segment(5, roll=True)
    assert frames[-1].drop_evidence.armed and frames[-1].drop_evidence.absent_beats >= 8
    assert all(s.state == "buildup" and s.drop_id == 0 for s in frames)


def test_pause_compensates_only_learned_melodic_bed_and_keeps_harmonic_bass_blocked():
    from dataclasses import replace
    from test_kick_identity import trained_identity
    gate = trained_identity()
    gate.references = deque(replace(r, peak_harmonic_db=-30, power_db=-20) for r in gate.references)
    event = KickEvent(105,105.02,1,.95)
    gate.prepared[105] = replace(descriptor(-20), harmonic_attack=.025)
    assert not gate.return_matches(event)
    assert gate.return_matches(event, after_pause=True)
    gate.prepared[105] = replace(descriptor(-20), harmonic_attack=.15)
    assert not gate.return_matches(event, after_pause=True)


@pytest.mark.parametrize("effect", ["musical", "phrase_show"])
def test_preserved_pause_keeps_lights_dark(effect):
    from beatlight.contracts import LightingInput
    from beatlight.lighting.engine import LightingEngine
    from beatlight.lighting.config import LightConfig, LightingControls
    from beatlight.music.grid import grid_clock
    scene = prepared_scene()
    silence = scene.segment(.5, silent=True)[-1]
    clock = grid_clock(silence.grid, silence.updated_at)
    data = LightingInput(True, True, beat=clock, structure=silence, confirmed_kicks=())
    frame = LightingEngine().render(data, LightingControls(LightConfig(light_effect=effect), armed=True), silence.updated_at)
    assert all(s.intensity == 0 for s in frame.states)
