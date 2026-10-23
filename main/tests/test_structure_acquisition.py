"""Aquisição de contexto sem relaxar o perfil acústico exigido no drop."""
from test_structure import Performance


def test_calm_pad_intro_has_context_before_grid_and_learns_first_groove():
    p = Performance()
    intro = p.segment(8, low=-65, high=-38, rms=-30, kicks=False, rate=0)
    assert intro[0].state == "warming"
    assert all(s.state == "breakdown" for s in intro if s.updated_at > 1.3)
    assert all(not s.reference_ready and s.drop_id == 0 for s in intro)
    returning = p.segment(5)
    assert returning[-1].reference_ready and returning[-1].state == "groove"
    assert all(s.state != "drop" for s in returning)


def test_regular_music_outside_preferred_bpm_still_gets_context():
    p = Performance()
    result = p.segment(8, kick_every=.8, rate=1.25)
    assert all(s.state != "warming" for s in result if s.updated_at > 1.3)
    assert result[-1].state == "groove" and not result[-1].reference_ready
    assert result[-1].grid.state == "learning"


def test_growing_snare_intro_can_build_without_authorizing_first_kick_as_drop():
    p = Performance()
    intro = p.segment(6, low=-65, high=-50, rms=-25, kicks=False,
        rate=8, percussion_rate=8, percussion_db=-25, rising=4)
    assert any(s.state == "buildup" for s in intro)
    assert max(s.tension for s in intro) > .4
    returning = p.segment(5)
    assert returning[-1].reference_ready
    assert all(s.drop_id == 0 for s in returning)


def test_long_breakdown_keeps_context_instead_of_starting_acquisition_again():
    p = Performance()
    p.groove()
    result = p.segment(65, low=-70, high=-40, rms=-30, kicks=False, rate=0)
    assert all(s.state == "breakdown" for s in result if s.updated_at > 8)
    assert result[-1].reference_ready and result[-1].grid.state == "predicting"


def test_restarting_after_silence_reacquires_context_without_old_roll_evidence():
    p = Performance()
    p.groove()
    p.segment(4, kicks=False, low=-65, rate=8, high=-30, rms=-25, rising=4)
    p.segment(2, kicks=False, low=-120, high=-120, rms=-120, rate=0)
    restarted = p.segment(3, low=-65, high=-40, rms=-30, kicks=False, rate=0)
    assert restarted[-1].state == "breakdown" and not restarted[-1].reference_ready
    assert all(s.state not in ("drop", "buildup") for s in restarted)
