from datetime import datetime
import json
from threading import Event
from time import monotonic,sleep
from beatlight.diagnostics.output_log import OutputJournal
from beatlight.diagnostics.pc_time import local_time


def wait(condition):
    until=monotonic()+3
    while not condition() and monotonic()<until:sleep(.005)
    assert condition()


def stop(journal):journal.close();wait(lambda:journal.closed)


def test_events_use_os_local_timezone_and_survive_restart_with_last_cause(tmp_path):
    journal=OutputJournal(tmp_path)
    journal.event('ERROR','output.frame_timeout','Prévia atrasada.',port='COM5',age_ms=800)
    journal.event('INFO','output.activated','Reativada.')
    stop(journal)
    rows=[json.loads(line) for line in journal.path.read_text(encoding='utf-8').splitlines()]
    error=next(row for row in rows if row['level']=='ERROR');at=datetime.fromisoformat(error['time'])
    assert at.utcoffset()==local_time(at.timestamp()).utcoffset() and at==datetime.fromisoformat(error['utc'])
    assert error['context']=={'port':'COM5','age_ms':800}
    restarted=OutputJournal(tmp_path)
    wait(lambda:any(r['code']=='output.frame_timeout' for r in restarted.snapshot()['events']))
    assert restarted.snapshot()['last_incident']['code']=='output.frame_timeout'
    assert restarted.session!=journal.session
    stop(restarted)


def test_slow_disk_cannot_block_producer_and_queues_and_context_are_bounded(tmp_path,monkeypatch):
    entered=Event();release=Event();original=OutputJournal._load
    def stalled(self):entered.set();release.wait(3);original(self)
    monkeypatch.setattr(OutputJournal,'_load',stalled)
    journal=OutputJournal(tmp_path,capacity=20,pending_limit=4)
    try:
        assert entered.wait(1)
        before=monotonic()
        for i in range(150):journal.event('INFO','test.event','Teste',number=i)
        assert monotonic()-before<.5
        for i in range(100):journal.sample(beat=i)
        data=journal.snapshot()
        assert len(data['events'])==20 and len(data['health'])==60
        assert len(journal._pending)==4 and data['writes_lost']>=147
        journal.event('ERROR','test.large','Limitado',large=[{'value':'x'*10000}]*1000)
        assert len(json.dumps(journal.snapshot()['last_incident']))<12_000
    finally:release.set();stop(journal)


def test_disk_failure_does_not_stop_in_memory_diagnostics(tmp_path):
    target=tmp_path/'not-a-directory';target.write_text('file',encoding='utf-8')
    journal=OutputJournal(target)
    wait(lambda:bool(journal.snapshot()['disk_error']))
    journal.event('ERROR','usb.transport_error','Falha simulada.',exception='TimeoutError')
    assert journal.snapshot()['last_incident']['context']['exception']=='TimeoutError'
    stop(journal)


def test_rotation_remains_limited_and_corrupt_history_is_ignored(tmp_path):
    (tmp_path/'pixel-output.jsonl').write_text('broken\n{}\n',encoding='utf-8')
    journal=OutputJournal(tmp_path,max_bytes=1000)
    for n in range(30):journal.event('INFO','test.rotation','R'*200,index=n)
    stop(journal)
    assert len(list(tmp_path.glob('pixel-output.jsonl*')))<=4
    assert all(path.stat().st_size<2000 for path in tmp_path.iterdir())
    restarted=OutputJournal(tmp_path,max_bytes=1000)
    wait(lambda:restarted.revision>1)
    assert all('code' in row for row in restarted.snapshot()['events'])
    stop(restarted)
