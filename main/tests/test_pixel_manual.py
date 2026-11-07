from copy import deepcopy
import pytest
from beatlight.pixel.project import PixelProjectStore,validate_project
from test_pixel import project


@pytest.mark.parametrize('effect',['standing','portals','zipper','diamonds','ribbons','silk'])
def test_new_manual_patterns_round_trip_without_altering_strip_configuration(tmp_path,effect):
    data=project();strips=deepcopy(data['strips'])
    data['show'].update(mode=effect,manualMode=True,manualPattern=effect)
    store=PixelProjectStore(tmp_path/'manual.json');store.save(data)
    assert store.load()==data and store.load()['strips']==strips


@pytest.mark.parametrize('changes',[dict(manualMode=1),dict(manualPattern='unknown'),dict(manualMode=True,manualPattern='wave'),dict(mode='wave',manualMode=True,manualPattern='silk')])
def test_invalid_manual_selection_cannot_overwrite_a_good_project(tmp_path,changes):
    data=project();store=PixelProjectStore(tmp_path/'manual.json');store.save(data)
    bad=deepcopy(data);bad['show'].update(changes)
    with pytest.raises(ValueError):store.save(bad)
    assert store.load()==data


def test_manual_memory_can_remain_inactive_while_auto_show_is_selected():
    data=project();data['show'].update(mode='auto',manualMode=False,manualPattern='silk')
    assert validate_project(data)==data
