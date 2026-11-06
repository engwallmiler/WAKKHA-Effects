"""PC timezone, including Windows processes launched with TZ=GMT0/UTC."""
from datetime import datetime,timezone
from functools import lru_cache
import os
from time import time

_WINDOWS=os.name=='nt'


@lru_cache(maxsize=1)
def _windows_converter():
    import ctypes
    from ctypes import wintypes
    class SystemTime(ctypes.Structure):
        _fields_=[(name,wintypes.WORD) for name in ('year','month','weekday','day','hour','minute','second','milliseconds')]
    convert=ctypes.WinDLL('kernel32',use_last_error=True).SystemTimeToTzSpecificLocalTimeEx
    convert.argtypes=[ctypes.c_void_p,ctypes.POINTER(SystemTime),ctypes.POINTER(SystemTime)]
    convert.restype=wintypes.BOOL
    return SystemTime,convert


def local_time(timestamp=None):
    utc=datetime.fromtimestamp(time() if timestamp is None else timestamp,timezone.utc)
    if _WINDOWS:
        # NULL selects the active Windows timezone with its dynamic DST rules.
        # Do not change TZ or process-global C runtime settings.
        try:
            import ctypes
            system_time,convert=_windows_converter()
            source=system_time(utc.year,utc.month,0,utc.day,utc.hour,utc.minute,utc.second,utc.microsecond//1000)
            target=system_time()
            if not convert(None,ctypes.byref(source),ctypes.byref(target)):raise OSError(ctypes.get_last_error())
            wall=datetime(target.year,target.month,target.day,target.hour,target.minute,target.second,utc.microsecond)
            return wall.replace(tzinfo=timezone(wall-utc.replace(tzinfo=None)))
        except (OSError,ValueError,OverflowError):pass
    return utc.astimezone()
