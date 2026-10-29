import json
from threading import Event
from time import monotonic,sleep
from beatlight.pixel.project import PixelProjectStore
from beatlight.pixel.project_writer import LatestProjectWriter
from beatlight.ui.pixel import PixelBridge
from test_pixel import project

def wait(condition,timeout=3):
    end=monotonic()+timeout
    while monotonic()<end:
        if condition():return
        sleep(.002)
    assert condition()

def test_slow_disk_keeps_only_latest_pending_save_and_flushes_on_close(tmp_path):
    started,release=Event(),Event();store=PixelProjectStore(tmp_path/'p.json');original=store.save
    def slow_save(data):started.set();release.wait(2);original(data)
    store.save=slow_save;writer=LatestProjectWriter(store)
    try:
        writer.submit(json.dumps(project()));assert started.wait(1)
        for i in range(1000):
            data=project();data['show']['brightness']=i/1000;writer.submit(json.dumps(data))
            assert writer.pending<=1
        assert writer.replaced>=998 and writer.busy
        writer.close();release.set();wait(lambda:writer.closed)
        assert store.load()['show']['brightness']==.999 and writer.writes==2
    finally:release.set();writer.close();wait(lambda:writer.closed)

def test_unchanged_saves_skip_io_and_invalid_payload_does_not_replace_good_file(tmp_path):
    store=PixelProjectStore(tmp_path/'p.json');messages=[];writer=LatestProjectWriter(store,messages.append);payload=json.dumps(project())
    try:
        writer.submit(payload);wait(lambda:writer.writes==1 and not writer.busy)
        assert not writer.submit(payload)
        writer.submit('{invalid');wait(lambda:bool(writer.error));assert store.load()==project()
        data=project();data['show']['brightness']=.2;writer.submit(json.dumps(data));wait(lambda:writer.writes==2 and not writer.busy)
        assert store.load()['show']['brightness']==.2 and any('não salvo' in message for message in messages)
    finally:writer.close();wait(lambda:writer.closed)

def test_pending_revert_is_not_lost_while_another_value_is_being_written(tmp_path):
    store=PixelProjectStore(tmp_path/'p.json');writer=LatestProjectWriter(store);gate=Event();entered=Event()
    first=project();second=project();second['show']['brightness']=.1
    try:
        writer.submit(json.dumps(first));wait(lambda:writer.writes==1 and not writer.busy)
        save=store.save
        def blocked(data):entered.set();gate.wait(2);save(data)
        store.save=blocked;writer.submit(json.dumps(second));assert entered.wait(1)
        writer.submit(json.dumps(first));writer.close();gate.set();wait(lambda:writer.closed)
        assert store.load()==first
    finally:gate.set();writer.close();wait(lambda:writer.closed)

def test_unresponsive_renderer_has_one_music_message_in_flight_and_only_the_latest_pending(tmp_path):
    bridge=PixelBridge(PixelProjectStore(tmp_path/'p.json'));bridge.ready_state=True;received=[];bridge.packet.connect(lambda value:received.append(json.loads(value)))
    bridge.send_music({'sample':0});token=received[0]['delivery_id']
    for sample in range(1,10001):bridge.send_music({'sample':sample})
    assert len(received)==1 and bridge._music_pending=={'sample':10000}
    bridge.musicConsumed(token+50);assert len(received)==1
    bridge.musicConsumed(token);assert len(received)==2 and received[-1]['sample']==10000
    bridge.musicConsumed(received[-1]['delivery_id']);assert bridge._music_pending is None and bridge._music_inflight is None
    bridge.writer.close();assert bridge.writer.closed

def test_preview_requires_an_explicit_request_not_an_old_operator_snapshot(tmp_path):
    bridge=PixelBridge(PixelProjectStore(tmp_path/'p.json'));requests=[];bridge.previewRequested.connect(lambda:requests.append(True))
    bridge.operatorState(json.dumps({'source':'demo','armed':True,'blackout':False,'manualDrop':False,'previewOnly':True}))
    assert requests==[]
    bridge.requestPreview();assert requests==[True]
    bridge.writer.close();assert bridge.writer.closed
