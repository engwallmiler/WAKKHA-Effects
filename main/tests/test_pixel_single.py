from copy import deepcopy
import pytest
from beatlight.pixel.project import EFFECTS,validate_project,PixelProjectStore
from test_pixel import project


@pytest.mark.parametrize('bars',[32,64,128])
def test_long_intervals_and_single_rules_round_trip(tmp_path,bars):
    data=project();data['show'].update(effectMix='single',sceneBars=bars,singleRules={'wave':dict(enabled=True,bars=128),'rain':dict(enabled=False,bars=0)})
    store=PixelProjectStore(tmp_path/'single.json');store.save(data);assert store.load()==data


@pytest.mark.parametrize('rules',[{'unknown':dict(enabled=True,bars=4)},{'wave':dict(enabled=True,bars=129)},
    {'wave':dict(enabled=True,bars=True)},{'wave':dict(enabled='yes',bars=4)},[],
    {effect:dict(enabled=False,bars=0) for effect in EFFECTS-{'inherit'}}])
def test_invalid_rules_do_not_replace_a_valid_project(tmp_path,rules):
    store=PixelProjectStore(tmp_path/'p.json');data=project();store.save(data)
    bad=deepcopy(data);bad['show']['singleRules']=rules
    with pytest.raises(ValueError):store.save(bad)
    assert store.load()==data
