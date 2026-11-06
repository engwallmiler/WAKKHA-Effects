from datetime import datetime,timezone
import os
import pytest
from beatlight.diagnostics.pc_time import local_time
import beatlight.diagnostics.pc_time as module


@pytest.mark.skipif(os.name!='nt',reason='Windows system timezone API')
@pytest.mark.parametrize('instant',['2026-11-06T02:05:17.123456+00:00','2026-01-01T01:30:00+00:00','2018-01-15T12:30:00+00:00','2018-07-15T12:30:00+00:00'])
def test_windows_timezone_matches_explicit_system_zone_even_with_utc_environment(instant,monkeypatch):
    from PySide6.QtCore import QDateTime,QTimeZone
    monkeypatch.setenv('TZ','GMT0')
    stamp=datetime.fromisoformat(instant).timestamp();result=local_time(stamp)
    expected=QDateTime.fromMSecsSinceEpoch(round(stamp*1000),QTimeZone.systemTimeZone())
    assert result.utcoffset().total_seconds()==expected.offsetFromUtc()
    assert result.timestamp()==stamp and result.hour==expected.time().hour()
    assert result.day==expected.date().day() and result.microsecond==datetime.fromisoformat(instant).microsecond


def test_non_windows_and_unavailable_windows_api_have_a_valid_fallback(monkeypatch):
    stamp=1793930717.123456
    monkeypatch.setattr(module,'_WINDOWS',False)
    assert local_time(stamp)==datetime.fromtimestamp(stamp,timezone.utc).astimezone()
    monkeypatch.setattr(module,'_WINDOWS',True)
    def failed():raise OSError('API indisponível')
    monkeypatch.setattr(module,'_windows_converter',failed)
    assert local_time(stamp)==datetime.fromtimestamp(stamp,timezone.utc).astimezone()
