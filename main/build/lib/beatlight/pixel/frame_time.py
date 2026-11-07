"""Conservative frame age across host and renderer monotonic clocks.

A queued JS request is not a generated frame. Causality gives a lower bound
on the host-minus-renderer offset; using that bound never makes old RGB newer.
Calibration is refreshed on fast replies, reused for at most one second, and
includes a generous drift margin. No session history or wall clock is used.
"""
from dataclasses import dataclass,asdict
import math
from time import get_clock_info


@dataclass(frozen=True,slots=True)
class FrameTiming:
    created_at: float
    age_bound_ms: float
    roundtrip_ms: float
    javascript_ms: float | None=None
    queue_lower_ms: float | None=None
    stamped: bool=False
    clock_reset: bool=False
    reference_age_ms: float=0

    def diagnostics(self):
        return {key:value for key,value in asdict(self).items() if key!='created_at'}


class FrameClock:
    def __init__(self,resolution=None):
        self.resolution=get_clock_info('monotonic').resolution if resolution is None else resolution
        if not math.isfinite(self.resolution) or self.resolution<0:raise ValueError('Resolução de relógio inválida.')
        self.reset()

    def reset(self):self._lower=None;self._epoch=None;self._reference_at=None

    def inspect(self,sent,received,stamp=None):
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (sent,received)) or received<sent:
            raise ValueError('Relógio do pedido de pixels inválido.')
        roundtrip=(received-sent)*1000
        if stamp is None:return FrameTiming(sent,roundtrip,roundtrip)
        if not isinstance(stamp,dict) or type(stamp.get('version')) is not int or stamp['version']!=1:raise ValueError('Carimbo temporal dos pixels inválido.')
        epoch,start,end=(stamp.get(key) for key in ('epoch','started_ms','completed_ms'))
        if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in (epoch,start,end)) or end<start:
            raise ValueError('Carimbo temporal dos pixels inválido.')
        start/=1000;end/=1000;r=self.resolution
        if end-start>received-sent+2*r+1e-6:raise ValueError('Tempo de cálculo dos pixels inconsistente.')
        reset=self._epoch is not None and self._epoch!=epoch
        if self._epoch!=epoch:self._lower=None;self._reference_at=None;self._epoch=epoch
        lower=sent-start-r;upper=received-end+r
        reference_age=received-self._reference_at if self._reference_at is not None else 0
        effective=self._lower-.001*reference_age if self._lower is not None else None
        if effective is not None and effective>upper+1e-6:
            # Clock discontinuity: fall back to the current causal interval.
            # A slow first request cannot establish a falsely fresh frame.
            self._lower=None;reset=True
        if self._lower is None or reference_age>1 or received-sent<=.1:
            self._lower=lower;self._reference_at=sent;effective=lower;reference_age=0
        created=min(received,start+effective-r)
        return FrameTiming(created,max(0,received-created)*1000,roundtrip,(end-start)*1000,
            max(0,start+effective-sent)*1000,True,reset,reference_age*1000)
