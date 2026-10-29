from copy import deepcopy
import pytest
from beatlight.pixel.project import validate_project,PixelProjectStore
from test_pixel import project

def layout():
    data=project();data['geometry']['lines']=[deepcopy(data['geometry']['lines'][0]) for _ in range(6)]
    data['strips']=[{**data['strips'][0],'id':f's{i}'} for i in range(6)]
    data['patch']={'version':1,'runs':[{'id':'cable','name':'Laterais','segments':[{'strip_id':'s0','reverse':False},{'strip_id':'s1','reverse':True}]}],
      'mirrors':[{'source':'cable','targets':[{'id':'s5','reverse':False},{'id':'s4','reverse':True}]}]}
    return data

def test_patch_roundtrip_preserves_identity_order_reverse_and_original_strip_controls(tmp_path):
    data=layout();store=PixelProjectStore(tmp_path/'project.json');store.save(data);assert store.load()==data
    legacy=project();assert validate_project(legacy)==legacy

def test_exact_copy_requires_matching_pixels_and_channel_format(tmp_path):
    data=layout();data['patch']['mirrors']=[{'source':'s0','mode':'exact','targets':[{'id':'s5','reverse':False}]}]
    store=PixelProjectStore(tmp_path/'exact.json');store.save(data);assert store.load()==data
    bad=deepcopy(data);bad['geometry']['lines'][5]['pixels']-=1
    with pytest.raises(ValueError,match='Cópia exata'):store.save(bad)
    assert store.load()==data
    bad=deepcopy(data);bad['strips'][5]['profile']='rgbw'
    with pytest.raises(ValueError,match='Cópia exata'):validate_project(bad)
    bad['patch']['mirrors'][0]['mode']='fit';assert validate_project(bad)==bad

def test_copy_mode_is_validated_and_legacy_groups_stay_proportional():
    data=layout();assert validate_project(data)==data
    data['patch']['mirrors'][0]['mode']='unknown'
    with pytest.raises(ValueError,match='Modo de cópia'):validate_project(data)

def test_partial_mirrors_work_inside_a_single_physical_cable():
    data=layout();data['patch']['runs']=[{'id':'cable','name':'Uma fita','segments':[{'strip_id':f's{i}','reverse':False} for i in range(6)]}]
    data['patch']['mirrors']=[{'source':'s0','targets':[{'id':'s5','reverse':False}]},{'source':'s1','targets':[{'id':'s4','reverse':True}]}]
    assert validate_project(data)==data
    data['patch']['mirrors'][0]['targets'].append({'id':'cable','reverse':False})
    with pytest.raises(ValueError):validate_project(data)

@pytest.mark.parametrize('kind',['duplicate_part','missing_part','bad_direction','colliding_id','empty_run','duplicate_target','chain','self','missing_root','bad_id_type','bad_source_type','bad_version','null'])
def test_invalid_wiring_is_rejected_without_replacing_a_valid_project(tmp_path,kind):
    data=layout();store=PixelProjectStore(tmp_path/'project.json');store.save(data);bad=deepcopy(data);patch=bad['patch']
    if kind=='duplicate_part':patch['runs'][0]['segments'].append({'strip_id':'s0','reverse':False})
    elif kind=='missing_part':patch['runs'][0]['segments'][0]['strip_id']='absent'
    elif kind=='bad_direction':patch['runs'][0]['segments'][0]['reverse']='no'
    elif kind=='colliding_id':patch['runs'][0]['id']='s2'
    elif kind=='empty_run':patch['runs'][0]['segments']=[]
    elif kind=='duplicate_target':patch['mirrors'].append({'source':'s3','targets':[{'id':'s5','reverse':False}]})
    elif kind=='chain':patch['mirrors'].append({'source':'s5','targets':[{'id':'s3','reverse':False}]})
    elif kind=='self':patch['mirrors'][0]['targets'][0]['id']='cable'
    elif kind=='missing_root':patch['mirrors'][0]['source']='missing'
    elif kind=='bad_id_type':patch['mirrors'][0]['targets'][0]['id']=[]
    elif kind=='bad_source_type':patch['mirrors'][0]['source']={}
    elif kind=='bad_version':patch['version']=True
    elif kind=='null':bad['patch']=None
    with pytest.raises(ValueError):store.save(bad)
    assert store.load()==data
