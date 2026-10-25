from types import SimpleNamespace
from beatlight.ui.pixel_usb import PixelUsbPanel


def test_blackout_invalidates_a_nonzero_sample_already_in_flight():
    calls=[]
    runtime=SimpleNamespace(blackout=lambda:calls.append('blackout'),submit=lambda *args:calls.append('frame'))
    panel=SimpleNamespace(page=SimpleNamespace(bridge=SimpleNamespace(operator={'blackout':True,'armed':True})),
        runtime=runtime,generation=7,pending=True,closing=False)
    PixelUsbPanel._operator_changed(panel)
    # A completed pre-blackout sample must not relight the strip after the command.
    PixelUsbPanel._frame(panel,'stale nonzero frame',7,'strip-1',0)
    assert calls==['blackout'] and not panel.pending


def test_other_operator_updates_do_not_cancel_a_valid_sample_or_flash_black():
    calls=[]
    panel=SimpleNamespace(page=SimpleNamespace(bridge=SimpleNamespace(operator={'blackout':False,'armed':True,'manualDrop':True})),
        runtime=SimpleNamespace(blackout=lambda:calls.append('blackout')),generation=7,pending=True)
    PixelUsbPanel._operator_changed(panel)
    assert calls==[] and panel.generation==7 and panel.pending
