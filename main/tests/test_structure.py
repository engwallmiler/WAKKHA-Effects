from collections import deque
from dataclasses import replace
import math
import pytest
from beatlight.contracts import KickEvent, StructureFeatures
from beatlight.music.structure import StructureTracker
from beatlight.music.tracker import BeatTracker


class Performance:
    def __init__(self):
        self.structure = StructureTracker()
        self.beats = BeatTracker()
        self.kicks = deque(maxlen=16)
        self.at = 0.0
        self.frame = 0
        self.last = None

    def segment(self, seconds, *, low=-20, high=-35, rms=-15, kicks=True, rate=2, rising=0, percussion_rate=0, percussion_db=-120, kick_every=0.5):
        snapshots = []
        start = self.at
        next_kick = math.ceil((start - 1e-7) / kick_every) * kick_every
        next_onset = start
        next_percussion = start
        while self.at < start + seconds - 1e-7:
            t = self.at
            if kicks and t >= next_kick - 1e-7:
                self.kicks.append(KickEvent(t, t + 0.02, 0.05, 0.95))
                next_kick += kick_every
            onset = rate > 0 and t >= next_onset - 1e-7
            if onset:
                next_onset = t + 1 / rate
            percussion_onset = percussion_rate > 0 and t >= next_percussion - 1e-7
            if percussion_onset:
                next_percussion = t + 1 / percussion_rate
            beat = self.beats.process(tuple(self.kicks), t)
            self.frame += 1
            f = StructureFeatures(self.frame, t, low, high + rising * (t - start), rms, 0.3, onset, percussion_onset, percussion_db)
            self.last = self.structure.process(f, tuple(self.kicks), beat)
            snapshots.append(self.last)
            self.at += 0.02
        return snapshots

    def groove(self):
        self.segment(6)
        assert self.last.state == "groove"


def test_relative_phrase_is_not_downbeat_detection_and_low_initial_strength_is_accepted():
    p = Performance()
    p.groove()
    snapshots = p.segment(4)
    counts = []
    for s in snapshots:
        if not counts or counts[-1] != s.phrase_kick:
            counts.append(s.phrase_kick)
        assert s.bar_beat == (s.phrase_kick - 1) % 4 + 1
        assert s.phrase_bar == (s.phrase_kick - 1) // 4 + 1
    assert set(counts) == set(range(1, 9))
    assert all(s.state == "groove" for s in snapshots)


def test_breakdown_builds_tension_then_drop_lasts_exactly_eight_unique_kicks():
    p = Performance()
    p.groove()
    broken = p.segment(3, low=-70, high=-35, rms=-25, kicks=False)
    assert broken[-1].state == "breakdown"
    rising = p.segment(5, low=-70, high=-35, rms=-25, kicks=False, rate=6, rising=2)
    assert rising[-1].state == "buildup"
    assert rising[-1].tension > broken[-1].tension + 0.25
    dropped = p.segment(4.5)
    counts = {s.drop_kicks for s in dropped if s.state == "drop"}
    assert counts == set(range(1, 9))
    assert dropped[0].state == "drop" and dropped[0].phrase_kick == 1
    assert dropped[-1].state == "groove"
    assert len([e for e in dropped[-1].events if e.kind == "drop"]) == 1


def test_refined_duplicate_kicks_do_not_advance_the_phrase():
    p = Performance()
    p.groove()
    before = p.last.phrase_kick
    refined = tuple(replace(k, intensity=1) for k in p.kicks)
    after = p.structure.process(StructureFeatures(1000, p.last.updated_at, -20, -35, -15, 0.2, False), refined, p.beats.process(refined, p.last.updated_at))
    assert after.phrase_kick == before


def test_growing_hats_over_a_continuing_groove_do_not_create_break_or_drop():
    p = Performance()
    p.groove()
    snapshots = p.segment(10, high=-35, rate=8, rising=1.5)
    assert {s.state for s in snapshots} == {"groove"}
    assert snapshots[-1].drop_id == 0


def test_intro_is_classified_without_grid_and_does_not_authorize_drop():
    p = Performance()
    snapshots = p.segment(10, low=-70, high=-35, rms=-25, kicks=False, rate=8, rising=1)
    assert snapshots[0].state == "warming"
    assert snapshots[-1].state == "breakdown"
    assert all(s.state != "warming" for s in snapshots if s.updated_at > 1.3)
    assert all(not s.reference_ready and s.grid.state == "learning" for s in snapshots)
    returning = p.segment(4)
    assert all(s.state != "drop" for s in returning)


def test_silence_clears_context_and_restart_is_not_a_drop():
    p = Performance()
    p.groove()
    p.segment(3, low=-70, high=-35, rms=-25, kicks=False)
    quiet = p.segment(2, low=-120, high=-120, rms=-120, kicks=False, rate=0)
    assert quiet[-1].state == "silence"
    returning = p.segment(5)
    assert all(s.state != "drop" for s in returning)
    assert returning[-1].state == "groove"


def test_no_kick_but_persistent_bass_is_not_a_breakdown():
    p = Performance()
    p.groove()
    snapshots = p.segment(5, kicks=False, low=-20)
    assert all(s.state == "groove" for s in snapshots)


def test_false_kick_without_bass_recovery_does_not_trigger_drop():
    p = Performance()
    p.groove()
    p.segment(3, low=-70, high=-35, rms=-25, kicks=False)
    snapshots = p.segment(1, low=-70, high=-30, rms=-25, kicks=True)
    assert all(s.state != "drop" for s in snapshots)
    assert snapshots[-1].drop_id == 0


def test_drop_without_following_kicks_expires_instead_of_holding_energy():
    p = Performance()
    p.groove()
    p.segment(3, low=-70, high=-35, rms=-25, kicks=False)
    p.segment(0.2)
    assert p.last.state == "drop"
    p.segment(3, low=-70, high=-35, rms=-25, kicks=False)
    assert p.last.state != "drop"


def test_reset_discards_phrase_and_breakdown_context():
    p = Performance()
    p.groove()
    p.segment(3, low=-70, high=-35, rms=-25, kicks=False)
    p.structure.reset()
    s = p.structure.process(StructureFeatures(1, 50, -70, -35, -25, 0.2, False))
    assert s.state == "warming" and s.drop_id == s.phrase_kick == 0
    assert not s.events


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_invalid_descriptors_are_rejected(value):
    with pytest.raises(ValueError):
        StructureTracker().process(StructureFeatures(1, 0, value, -35, -15, 0.2, False))


def test_time_must_not_move_backwards():
    tracker = StructureTracker()
    tracker.process(StructureFeatures(1, 2, -20, -35, -15, 0.2, False))
    with pytest.raises(ValueError):
        tracker.process(StructureFeatures(2, 1, -20, -35, -15, 0.2, False))


def test_brightening_without_more_volume_or_faster_onsets_can_build_tension():
    p = Performance()
    p.groove()
    p.segment(3, low=-70, high=-35, rms=-25, kicks=False)
    before = p.last.tension
    for i in range(200):
        t = p.at
        p.last = p.structure.process(StructureFeatures(1000 + i, t, -70, -35, -25,
            0.3 + i / 500, i % 25 == 0), tuple(p.kicks), p.beats.process(tuple(p.kicks), t))
        p.at += 0.02
    assert p.last.state == "buildup"
    assert p.last.tension > before + 0.08


def test_long_descriptor_gap_invalidates_old_tension_context():
    p = Performance()
    p.groove()
    p.segment(3, low=-70, high=-35, rms=-25, kicks=False)
    s = p.structure.process(StructureFeatures(1000, p.at + 10, -20, -35, -15, 0.3, True))
    assert s.state == "warming" and s.tension == 0
    assert s.phrase_kick == s.drop_id == 0


def test_roll_already_fast_at_breakdown_entry_is_detected_without_volume_growth():
    p = Performance()
    p.groove()
    result = p.segment(4, low=-70, high=-35, rms=-25, kicks=False, rate=8)
    assert result[-1].state == "buildup"
    assert result[-1].tension > 0.4


def test_midrange_roll_builds_while_kicks_and_bass_continue_without_false_drop():
    p = Performance()
    p.segment(6, percussion_rate=2, percussion_db=-40)
    assert p.last.state == "groove"
    result = p.segment(5, percussion_rate=8, percussion_db=-30, rate=8)
    assert result[-1].state == "buildup"
    assert result[-1].roll_rate > 6
    assert all(s.state != "drop" for s in result)
    changes = [b.state for a, b in zip(result, result[1:]) if a.state != b.state]
    assert changes == ["buildup"]


def test_roll_with_sustained_bass_and_missing_kick_can_build():
    p = Performance()
    p.segment(6, percussion_rate=2, percussion_db=-40)
    result = p.segment(4, low=-20, kicks=False, rate=8, percussion_rate=8, percussion_db=-30)
    assert result[-1].state == "buildup"


def test_short_roll_burst_is_not_promoted_to_build_up():
    p = Performance()
    p.segment(6, percussion_rate=2, percussion_db=-40)
    burst = p.segment(0.25, percussion_rate=12, percussion_db=-20, rate=12)
    result = p.segment(3, percussion_rate=2, percussion_db=-40)
    assert all(s.state == "groove" for s in burst + result)


def test_fast_percussion_that_was_already_in_the_learned_groove_is_not_new_build_up():
    p = Performance()
    p.segment(6, percussion_rate=8, percussion_db=-30, rate=8)
    result = p.segment(4, percussion_rate=8, percussion_db=-30, rate=8)
    assert all(s.state == "groove" for s in result)


def test_missing_confirmations_with_sustained_bass_do_not_truncate_eight_kicks():
    p = Performance()
    p.groove()
    p.segment(3, low=-70, high=-35, rms=-25, kicks=False)
    p.segment(.2)
    assert p.last.state == "drop" and p.last.drop_kicks == 1
    # Uma longa lacuna de confirmação mantém música/graves presentes.
    held = p.segment(4, kicks=False)
    assert all(s.state == "drop" and s.drop_kicks == 1 for s in held)
    resumed = p.segment(4)
    assert {s.drop_kicks for s in resumed if s.state == "drop"} >= set(range(2,9))
    assert resumed[-1].state == "groove"


def test_sparse_confirmed_kicks_survive_old_absolute_drop_timeout():
    p = Performance()
    p.groove()
    p.segment(3, low=-70, high=-35, rms=-25, kicks=False)
    result = p.segment(12.2, kick_every=1.5)
    assert {s.drop_kicks for s in result if s.state == "drop"} == set(range(1,9))
    assert any(s.state == "drop" and s.updated_at - s.drop_at > 8 for s in result)
    assert result[-1].state == "groove"
