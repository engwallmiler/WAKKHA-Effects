"""Bounded output flight recorder. Disk I/O never runs in the GUI/USB threads."""
from collections import deque
from datetime import timezone
import json
import logging
from logging.handlers import RotatingFileHandler
import math
import os
from itertools import islice
from pathlib import Path
from threading import Event, Lock, Thread
from time import monotonic
from uuid import uuid4
from beatlight import __version__
from beatlight.diagnostics.pc_time import local_time


def _bounded(value, depth=0):
    if value is None or type(value) in (bool, int):return value
    if isinstance(value, float):return round(value, 4) if math.isfinite(value) else str(value)
    if isinstance(value, str):return value[:512]
    if depth >= 3:return str(type(value).__name__)
    if isinstance(value, dict):return {str(k)[:64]:_bounded(v, depth+1) for k,v in islice(value.items(),16)}
    if isinstance(value, (tuple, list, deque)):return [_bounded(v, depth+1) for v in islice(value,16)]
    return str(value)[:512]


class OutputJournal:
    """1,000 events, 60 health samples, 256 pending writes, 4 × 2 MB files."""
    def __init__(self, directory: Path, *, capacity=1000, pending_limit=256, max_bytes=2_000_000):
        self.directory=Path(directory);self.path=self.directory/'pixel-output.jsonl'
        self.session=uuid4().hex[:12];self.started=monotonic()
        self._lock=Lock();self._wake=Event();self._stop=Event()
        self._events=deque(maxlen=capacity);self._pending=deque(maxlen=pending_limit)
        self._samples=deque(maxlen=60);self._revision=0;self._sequence=0
        self._error='';self._lost=0;self._last_incident=None;self._max_bytes=max_bytes
        self._thread=Thread(target=self._run, name='pixel-log', daemon=True);self._thread.start()
        self.event('INFO','session.started','Registro da saída iniciado.', version=__version__, pid=os.getpid())

    @property
    def closed(self):return not self._thread.is_alive()

    @property
    def revision(self):
        with self._lock:return self._revision

    def event(self, level, code, message, **context):
        now=local_time()
        record={'time':now.isoformat(timespec='milliseconds'), 'utc':now.astimezone(timezone.utc).isoformat(timespec='milliseconds'),
                'level':level, 'code':code, 'message':message[:512], 'session':self.session,
                'elapsed_s':round(monotonic()-self.started,3), 'context':_bounded(context)}
        if len(json.dumps(record['context'],ensure_ascii=False))>6000:record['context']={'summary':json.dumps(record['context'],ensure_ascii=False)[:5800],'truncated':True}
        with self._lock:
            if self._stop.is_set():return
            self._sequence+=1;record['sequence']=self._sequence
            self._events.append(record);self._revision+=1
            if level in ('WARNING','ERROR'):self._last_incident=record
            if len(self._pending)==self._pending.maxlen:self._lost+=1
            self._pending.append(record)
        self._wake.set()

    def sample(self, **context):
        record={'time':local_time().isoformat(timespec='milliseconds'), **_bounded(context)}
        with self._lock:self._samples.append(record)

    def snapshot(self):
        with self._lock:
            # All records are immutable after insertion; JSON export happens off-thread.
            return {'version':1,'application':__version__,'session':self.session,
                    'exported_at':local_time().isoformat(timespec='milliseconds'),
                    'events':list(self._events),'health':list(self._samples),
                    'last_incident':self._last_incident,'disk_error':self._error,'writes_lost':self._lost,
                    'limits':{'events':self._events.maxlen,'health':60,'pending':self._pending.maxlen,'disk_files':4,'file_bytes':self._max_bytes}}

    def close(self):
        if not self._stop.is_set():self.event('INFO','session.closed','Registro da saída encerrado.')
        self._stop.set();self._wake.set()

    def _load(self):
        history=deque(maxlen=self._events.maxlen)
        for path in [self.path.with_name(self.path.name+f'.{n}') for n in (3,2,1)]+[self.path]:
            try:
                if path.stat().st_size>self._max_bytes+16_384:continue
                with path.open(encoding='utf-8') as stream:
                    for line in stream:
                        if len(line)>16_384:continue
                        try:record=json.loads(line)
                        except ValueError:continue
                        if isinstance(record,dict) and all(isinstance(record.get(k),str) for k in ('time','code','level','message')):history.append(record)
            except OSError:continue
        with self._lock:
            current=list(self._events)
            self._events=deque([*history,*current], maxlen=self._events.maxlen)
            if self._last_incident is None:self._last_incident=next((r for r in reversed(history) if r['level'] in ('WARNING','ERROR')),None)
            self._revision+=1

    def _run(self):
        handler=None
        try:
            self._load();self.directory.mkdir(parents=True,exist_ok=True)
            handler=RotatingFileHandler(self.path,maxBytes=self._max_bytes,backupCount=3,encoding='utf-8')
            # Handler.handleError normally prints and swallows disk errors.
            def failure(record):
                with self._lock:self._error='Falha ao gravar o log em disco; os eventos recentes continuam na memória.';self._revision+=1
            handler.handleError=failure
        except OSError as exc:
            with self._lock:self._error=str(exc);self._revision+=1
        try:
            while True:
                self._wake.clear()
                with self._lock:
                    batch=list(self._pending);self._pending.clear();done=self._stop.is_set()
                if handler:
                    for row in batch:
                        record=logging.LogRecord('beatlight.output',logging.INFO,'',0,json.dumps(row,ensure_ascii=False),(),None)
                        handler.emit(record)
                if done:return
                self._wake.wait(.5)
        finally:
            if handler:handler.close()
