"""Projetos de fitas, frames RGB e ponte musical sem navegador/hardware."""
from copy import deepcopy
from dataclasses import replace
import json
import math
import pytest
from beatlight.pixel.project import PixelProjectStore,validate_project
from beatlight.pixel.protocol import music_packet,validate_frame
from beatlight.pixel.rendering import configure_renderer
from beatlight.contracts import KickEvent,RuntimeStatus
from beatlight.sync.timeline import apply_link
from test_link_sync import monitor,connected


def project():
    return {"version":1,"geometry":{"version":1,"lines":[{"name":"Fita A","start":{"x":100,"y":460},"end":{"x":100,"y":60},"meters":5,"leds":600,"pixels":200}]},
            "strips":[{"id":"a","enabled":True,"profile":"ws2811","effect":"wave","palette":"red","response":"hybrid","brightness":.8,"speed":1.2,"phase":0,"reverse":False}],
            "show":{"mode":"organic","brightness":.8,"followStructure":True}}


def status(**changes):
    return replace(RuntimeStatus("running","",0,0,0,0,0,None),**changes)


def test_project_atomic_roundtrip_and_invalid_save_preserves_last_valid(tmp_path):
    store=PixelProjectStore(tmp_path/"pixel-studio.json")
    assert store.load() is None
    data=project();store.save(data);assert store.load()==data
    bad=deepcopy(data);bad["strips"][0]["speed"]=float('nan')
    with pytest.raises(ValueError):store.save(bad)
    assert store.load()==data
    assert list(tmp_path.glob('*.tmp'))==[]


@pytest.mark.parametrize("section,field,value",[("strips","profile","dmx"),("strips","effect","unknown"),("strips","brightness",2),
    ("strips","speed",math.inf),("strips","phase",-1),("strips","enabled",1),("strips","response","predicted-kick"),
    ("show","mode","dropseq"),("show","armed",True),("show","bpm",500),("show","solidColor",[0,1,256])])
def test_invalid_project_cannot_change_operational_or_pixel_controls(section,field,value):
    data=project()
    (data[section][0] if section=="strips" else data[section])[field]=value
    with pytest.raises(ValueError):validate_project(data)


@pytest.mark.parametrize("value",[None,[],{},[project()["geometry"]["lines"][0]]*33])
def test_invalid_geometry_rejected(value):
    data=project();data["geometry"]=value
    with pytest.raises(ValueError):validate_project(data)


def test_duplicate_strip_ids_and_excess_pixels_rejected():
    data=project();data["geometry"]["lines"]*=2;data["strips"]*=2
    with pytest.raises(ValueError):validate_project(data)
    data=project();data["geometry"]["lines"][0]["pixels"]=601
    with pytest.raises(ValueError):validate_project(data)


def test_link_beat_is_continuous_without_manufacturing_kick_and_preserves_music():
    routed=apply_link(monitor(),connected(),10.1)
    packet=music_packet(routed,status(),10.2)
    assert packet["active"] and packet["audible"]
    assert packet["clock"]["beat"]==pytest.approx(16.65)
    assert packet["clock"]["source"]=="link" and packet["clock"]["bpm"]==120
    assert packet["kick"] is None and packet["music"]["drop_id"]==0


@pytest.mark.parametrize("change",["stopped","stale","silent","no-snapshot"])
def test_missing_or_quiet_audio_does_not_emit_audible_packet(change):
    snapshot=monitor();runtime=status()
    if change=="stopped":runtime=status(state="stopped")
    if change=="stale":runtime=status(audio_age=.6)
    if change=="silent":snapshot=replace(snapshot,silent=True)
    if change=="no-snapshot":snapshot=None
    assert not music_packet(snapshot,runtime,10.1)["audible"]


def test_only_confirmed_acoustic_events_are_forwarded_as_kicks():
    snapshot=monitor()
    event=KickEvent(10,10.03,.8,.9)
    structure=replace(snapshot.structure,confirmed_kicks=(event,))
    packet=music_packet(replace(snapshot,structure=structure),status(),10.1)
    assert packet["kick"]=={"id":10,"age":pytest.approx(.1),"strength":.8}
    assert music_packet(replace(snapshot,structure=structure,kick_error="broken"),status(),10.1)["kick"] is None
    json.dumps(packet,allow_nan=False)


def frame():
    return {"version":1,"physical_output":False,"strips":[{"id":"a","profile":"ws2811","model":"RGB","pixels":2,"data":[255,0,0,0,0,255]}]}


def test_ws2812_project_preserves_individual_300_led_resolution():
    data=project();data['strips'][0]['profile']='ws2812'
    data['geometry']['lines'][0].update(leds=300,pixels=300)
    assert validate_project(data)['geometry']['lines'][0]['pixels']==300


def test_ws2812_export_is_rgb_and_rejects_a_fictional_white_emitter():
    data=frame();data['strips'][0]['profile']='ws2812'
    assert validate_frame(data)['strips'][0]['model']=='RGB'
    data['strips'][0].update(model='RGBW',data=[0]*8)
    with pytest.raises(ValueError):validate_frame(data)


def test_rgb_frame_contains_one_rgb_triplet_per_addressable_pixel():
    assert validate_frame(frame())["strips"][0]["data"]==[255,0,0,0,0,255]


def test_software_renderer_is_enabled_before_chromium_without_disabling_its_sandbox():
    env={"QTWEBENGINE_CHROMIUM_FLAGS":"--enable-logging"}
    assert configure_renderer(env)=="software"
    assert "--disable-gpu" in env["QTWEBENGINE_CHROMIUM_FLAGS"].split()
    assert "--disable-gpu-compositing" in env["QTWEBENGINE_CHROMIUM_FLAGS"].split()
    assert "--no-sandbox" not in env["QTWEBENGINE_CHROMIUM_FLAGS"]
    assert env["QT_QUICK_BACKEND"]=="software"
    previous=env.copy();configure_renderer(env);assert previous==env


def test_explicit_gpu_renderer_override_is_preserved():
    env={"BEATLIGHT_PIXEL_RENDERER":"gpu"}
    assert configure_renderer(env)=="gpu" and "QTWEBENGINE_CHROMIUM_FLAGS" not in env


@pytest.mark.parametrize("change",["white","width","nonfinite","duplicate","real-output"])
def test_invalid_frame_cannot_be_used_as_ws2811_output(change):
    data=frame()
    if change=="white":data["strips"][0].update(model="RGBW",data=[0]*8)
    if change=="width":data["strips"][0]["data"].pop()
    if change=="nonfinite":data["strips"][0]["data"][0]=math.nan
    if change=="duplicate":data["strips"]*=2
    if change=="real-output":data["physical_output"]=True
    with pytest.raises(ValueError):validate_frame(data)
