from dataclasses import replace
from beatlight.contracts import KickEvent, StructureFeatures
from beatlight.music.kick_identity import KickIdentity


SHAPE = (0.0, 0.8, 0.6, 0.0)


def attack(gate, start, shape=SHAPE, decay=100, learn=False):
    event = KickEvent(start, start + 0.02, 0.3, 0.9)
    emitted = []
    for i in range(18):
        age = i / 100
        f = StructureFeatures(i, start + age, -15 - decay * age, -35, -12, 0.2, False, low_shape=shape)
        events = gate.push(f, (replace(event, intensity=min(1, i / 10)),))
        for accepted in events:
            gate.accept(accepted, learn)
            emitted.append(accepted)
    return emitted


def trained_identity():
    gate = KickIdentity()
    for i in range(8):
        assert len(attack(gate, 100 + i * 0.5, learn=True)) == 1
    return gate


def test_sustained_bass_with_same_spectrum_does_not_confirm_a_drop_kick():
    gate = trained_identity()
    assert attack(gate, 105, decay=0) == []
    assert gate.rejected == 1


def test_different_low_spectrum_does_not_confirm_a_drop_kick():
    gate = trained_identity()
    assert attack(gate, 105, shape=(0, 0, 0.2, 0.98)) == []
    assert gate.rejected == 1


def test_similar_kick_is_confirmed_once_after_its_short_decay():
    gate = trained_identity()
    events = attack(gate, 105, shape=(0.05, 0.78, 0.62, 0.03), decay=80)
    assert len(events) == 1
    assert events[0].occurred_at == 105
    assert gate.rejected == 0 and len(gate.references) == 8
    assert not gate.pending and not gate.prepared


def test_harmonic_bass_attack_with_kick_like_shape_and_decay_is_rejected():
    gate = trained_identity()
    event = KickEvent(105,105,1,0.95)
    emitted = []
    for i in range(18):
        age=i/100
        f=StructureFeatures(i,105+age,-15-100*age,-35,-12,0.2,False,low_shape=SHAPE,harmonic_db=-20-100*age)
        emitted.extend(gate.push(f,(event,)))
    assert emitted == []
    assert gate.rejected_harmonics == 1
