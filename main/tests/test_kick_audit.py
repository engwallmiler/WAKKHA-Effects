from dataclasses import replace
from beatlight.contracts import KickEvent, KickGridSnapshot, StructureSnapshot
from beatlight.music.kick_audit import KickAudit


def structure(at,confirmed=(),acoustic=()):
    grid=KickGridSnapshot(at,"tracking",0.5,100,0.9,5,at+0.5)
    return StructureSnapshot(at,"groove",0,0.9,0.5,0.3,2,0,1,1,1,0,0,None,None,0.5,"test",(),grid=grid,confirmed_kicks=confirmed,acoustic_kicks=acoustic)


def test_expected_empty_beats_are_reported_without_creating_kicks():
    audit=KickAudit()
    for i in range(100):
        at=100+i*0.05
        result=audit.process(structure(at),())
    assert result.expected_count>=9 and result.missed_count==result.expected_count
    assert result.confirmed_count==result.acoustic_count==0
    assert all(verdict=="sem kick" for _,verdict in result.slots)


def test_acoustic_offbeats_remain_separate_from_grid_confirmations():
    audit=KickAudit()
    events=()
    for i in range(100):
        at=100+i*0.05
        if i%10==5:
            events=events+(KickEvent(at,at,1,0.9),)
        result=audit.process(structure(at,acoustic=events),events)
    assert result.acoustic_count==10 and result.confirmed_count==0
    assert result.matched_count==0 and result.missed_count>=9


def test_only_observed_coherent_kicks_fill_expected_slots_once():
    audit=KickAudit()
    events=()
    for i in range(100):
        at=100+i*0.05
        if i%10==0:
            events=events+(KickEvent(at,at,1,0.9),)
        result=audit.process(structure(at,events,events),events)
    assert result.confirmed_count==10 and result.acoustic_count==10
    assert result.matched_count==result.expected_count>=9 and result.missed_count==0


def test_phase_correction_restarts_pending_slots_without_recounting_kicks():
    audit = KickAudit()
    events = (KickEvent(100, 100, 1, 0.9),)
    for i in range(61):
        at = 100 + i * 0.05
        before = audit.process(structure(at, events, events), events)
    for i in range(61, 91):
        at = 100 + i * 0.05
        current = structure(at, events, events)
        current = replace(current, grid=replace(current.grid, anchor_at=100.2, revision=1))
        after = audit.process(current, events)
    assert after.confirmed_count == before.confirmed_count == 1
    assert before.expected_count <= after.expected_count <= before.expected_count + 4
    assert all(abs((target - 100.2) / 0.5 - round((target - 100.2) / 0.5)) < 1e-7 for target, verdict in after.slots)
