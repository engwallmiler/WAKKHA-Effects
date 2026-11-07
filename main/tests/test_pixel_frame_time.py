import math
import random
import pytest
from beatlight.pixel.frame_time import FrameClock


def stamp(start,end=None,epoch=1):
    return dict(version=1,epoch=epoch,started_ms=start*1000,completed_ms=(start if end is None else end)*1000)


def test_594ms_queued_request_returns_fresh_rgb_after_clock_calibration():
    clock=FrameClock(resolution=0)
    first=clock.inspect(100,100.016,stamp(1,1.002))
    assert first.created_at==100
    delayed=clock.inspect(100.047,100.641,stamp(1.630,1.633))
    assert delayed.roundtrip_ms==pytest.approx(594)
    assert 11<=delayed.age_bound_ms<13
    assert delayed.javascript_ms==pytest.approx(3)
    assert 581<delayed.queue_lower_ms<=583
    assert delayed.created_at>100.6


def test_callback_delayed_after_generation_stays_old_and_slow_sampling_also_stays_old():
    clock=FrameClock(resolution=0);clock.inspect(100,100.016,stamp(1,1.002))
    delivered_late=clock.inspect(100.047,100.641,stamp(1.047,1.049))
    assert 594<=delivered_late.age_bound_ms<596
    slow_sampling=clock.inspect(101,101.61,stamp(2,2.6))
    assert slow_sampling.age_bound_ms>=600 and slow_sampling.javascript_ms==pytest.approx(600)


def test_first_slow_request_and_legacy_frames_cannot_claim_freshness():
    clock=FrameClock(resolution=0)
    assert clock.inspect(100,100.6,stamp(9,9.001)).age_bound_ms==pytest.approx(600)
    assert clock.inspect(101,101.6).created_at==101


def test_epoch_changes_and_clock_discontinuities_recalibrate_conservatively():
    clock=FrameClock(resolution=0);clock.inspect(100,100.01,stamp(1))
    result=clock.inspect(101,101.6,stamp(.6,epoch=2))
    assert result.clock_reset and result.age_bound_ms==pytest.approx(600)
    clock.inspect(102,102.01,stamp(1.6,epoch=2))
    jumped=clock.inspect(103,103.6,stamp(10,epoch=2))
    assert jumped.clock_reset and jumped.age_bound_ms==pytest.approx(600)
    clock.reset();assert clock.inspect(104,104.6,stamp(1)).age_bound_ms==pytest.approx(600)


@pytest.mark.parametrize('bad',[{},dict(version=True),dict(version=2),stamp(-1),stamp(2,1),stamp(math.inf),stamp(math.nan),stamp(1,epoch=True)])
def test_invalid_stamps_are_rejected(bad):
    with pytest.raises(ValueError):FrameClock().inspect(100,100.1,bad)


def test_impossible_execution_duration_is_rejected():
    with pytest.raises(ValueError):FrameClock(resolution=0).inspect(100,100.01,stamp(1,2))


def test_quantized_windows_clock_never_underestimates_actual_age_during_long_sessions():
    rng=random.Random(42);resolution=.015625;offset=99;clock=FrameClock(resolution=resolution)
    current=100.
    for _ in range(20000):
        sent=current+rng.random()*.1;queue=rng.random()*.7;sampling=rng.random()*.008;delivery=rng.random()*.4
        start=sent+queue;end=start+sampling;received=end+delivery
        host=lambda t:math.floor(t/resolution)*resolution
        result=clock.inspect(host(sent),host(received),stamp(start-offset,end-offset))
        actual_age=received-start
        assert result.age_bound_ms+1e-6>=actual_age*1000
        assert result.created_at<=host(received)
        current=received+1
    assert not hasattr(clock,'history')


def test_calibration_cannot_age_for_hours_or_hide_renderer_clock_drift():
    clock=FrameClock(resolution=.015625);resolution=.015625;offset=99
    host=lambda t:math.floor(t/resolution)*resolution
    renderer=lambda t:(t-offset)*1.0001
    for hour in range(49):
        current=100+hour*3600
        for i in range(20):
            sent=current;queue=.55 if i==19 else .003;start=sent+queue;end=start+.002;received=end+.01
            result=clock.inspect(host(sent),host(received),stamp(renderer(start),renderer(end)))
            assert result.age_bound_ms>=12-1e-6 and result.reference_age_ms<=1000
            current=received+.03
    sent=current+2
    old_reference=clock.inspect(sent,sent+.6,stamp(renderer(sent+.58),renderer(sent+.582)))
    assert old_reference.age_bound_ms>=600  # No stale calibration reused indefinitely.
