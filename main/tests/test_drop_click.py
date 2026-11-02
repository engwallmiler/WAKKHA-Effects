import pytest
from beatlight.configuration.store import Settings
from beatlight.dsp.pipeline import AudioAnalyzer
from drop_click_signals import click_scene
from test_kicks import blocks


def run_scene(**options):
    rate=options.get('rate',48000)
    samples=click_scene(**options)
    analyzer=AudioAnalyzer(beat_config=Settings().beat_config())
    drops=[]
    for block in blocks(samples,rate=rate):
        result=analyzer.process(block)
        assert not result.structure_error and not result.kick_error
        if result.structure and result.structure.state=='drop':
            drops.append((block.acquired_at+block.frames/rate,result.structure))
    return drops,analyzer


@pytest.mark.parametrize('options',[{}, {'level':1.2}, {'gain':.15,'rate':44100}])
def test_learned_click_recovers_first_masked_kick_and_all_eight_real_positions(options):
    drops,analyzer=run_scene(**options)
    assert drops and 12<=drops[0][0]<12.15
    assert drops[0][1].drop_evidence.click_supported
    assert {s.drop_kicks for _,s in drops}==set(range(1,9))
    assert drops[0][1].drop_at==pytest.approx(12,abs=.025)
    assert len(analyzer._structure._identity.references)<=16
    assert len(analyzer._structure_features._click.history)<=120
    assert analyzer._structure._last_kick>16.45  # continua em groove após os oito


@pytest.mark.parametrize('kind',['bass_only','crash','pluck'])
def test_click_with_no_compatible_kick_does_not_create_a_drop(kind):
    drops,_=run_scene(kind=kind)
    assert not drops


@pytest.mark.parametrize('options',[{'click':'return_only'}, {'offset':.09}])
def test_unlearned_or_late_click_does_not_enable_the_masked_exception(options):
    drops,_=run_scene(**options)
    assert all(not s.drop_evidence.click_supported for _,s in drops)


def test_doubled_weak_kicks_with_click_do_not_fire_before_the_real_drop():
    drops,_=run_scene(kind='weak_roll')
    assert drops and min(at for at,_ in drops)>=12
    assert drops[0][0]<12.15
