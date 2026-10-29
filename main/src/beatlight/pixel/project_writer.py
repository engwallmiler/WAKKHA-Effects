"""Salvamento fora da UI: um pedido em execução e somente o último pendente."""
import json
from threading import Condition,Thread
from beatlight.pixel.project import MAX_BYTES


class LatestProjectWriter:
    def __init__(self,store,notify=lambda message:None):
        self.store=store;self.notify=notify;self._condition=Condition();self._thread=None
        self._pending=self._active=self._last=None;self._closing=False
        self.writes=self.replaced=0;self.error=''

    def submit(self,payload):
        if not isinstance(payload,str) or len(payload)>MAX_BYTES:raise ValueError('Projeto excede 500 KB.')
        with self._condition:
            if self._closing:raise RuntimeError('Salvamento já está encerrando.')
            if payload==self._pending or self._pending is None and payload==(self._active if self._active is not None else self._last):return False
            if self._pending is not None:self.replaced+=1
            self._pending=payload
            if self._thread is None:
                self._thread=Thread(target=self._run,name='pixel-project-writer',daemon=True);self._thread.start()
            self._condition.notify();return True

    def _run(self):
        while True:
            with self._condition:
                self._condition.wait_for(lambda:self._pending is not None or self._closing)
                if self._pending is None and self._closing:return
                payload=self._pending;self._pending=None;self._active=payload
            try:
                if payload!=self._last:
                    self.store.save(json.loads(payload));self.writes+=1;self._last=payload
                self.error='';message='Projeto de fitas salvo automaticamente.'
            except (OSError,ValueError,TypeError,KeyError) as exc:
                self.error=str(exc);message=f'Projeto não salvo: {exc}'
            finally:
                with self._condition:self._active=None;self._condition.notify_all()
            self.notify(message)

    def close(self):
        with self._condition:self._closing=True;self._condition.notify_all()

    @property
    def closed(self):
        with self._condition:return self._closing and (self._thread is None or not self._thread.is_alive())

    @property
    def pending(self):
        with self._condition:return int(self._pending is not None)

    @property
    def busy(self):
        with self._condition:return self._active is not None
