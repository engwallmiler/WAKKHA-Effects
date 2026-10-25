"""Ensaio do HTML embutido, WebChannel, áudio sintético e perfis RGB independentes."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
# A sessão automatizada já está isolada; o sandbox aninhado do Chromium impede
# o subprocesso de renderização neste ambiente. Esta opção pertence só ao QA.
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS","--disable-gpu --disable-gpu-compositing --no-sandbox")
os.environ.setdefault("QT_OPENGL","software")
os.environ.setdefault("QT_QUICK_BACKEND","software")
import json
from pathlib import Path
import sys
from time import monotonic,sleep
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE
from beatlight.pixel.project import validate_project
from beatlight.pixel.protocol import validate_frame
from beatlight import __version__

root=Path(__file__).resolve().parents[1]
smoke="--smoke" in sys.argv
app=QApplication([]); app.setStyle("Fusion"); app.setStyleSheet(STYLE)
if os.name=="nt":
    for name in ("segoeui.ttf","segoeuib.ttf","seguisym.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/"+name)

def pump(condition,timeout=10):
    end=monotonic()+timeout
    while monotonic()<end:
        app.processEvents()
        if condition():return
        sleep(.005)
    assert condition(),"Tempo esgotado na integração do Pixel Studio: "+(window.pixel_page.notice.text()+str(window.pixel_page.load_events) if 'window' in globals() else '')

window=MainWindow(SettingsStore(root/".runtime"/"pixel-qa"/"preferences.json"),Settings(source="structure_demo"))
window.show();window._navigate(9)

def js(expression):
    result={}
    window.pixel_page.webpage.runJavaScript("JSON.stringify("+expression+")",lambda value:result.update(value=value))
    pump(lambda:"value" in result)
    assert result["value"],window.pixel_page.notice.text()
    return json.loads(result["value"])

report={"physical_output":False,"errors":[]}
def wait_seconds(seconds):
    end=monotonic()+seconds
    while monotonic()<end:app.processEvents();sleep(.005)

def check_tiles():
    checks=[]
    for element in ('sourceMode','stripEffect','cueBars','sourceMode'):
        js(f"(document.getElementById('{element}').scrollIntoView({{block:'center',behavior:'instant'}}),true)")
        wait_seconds(1)
        rect=js(f"(()=>{{const r=document.getElementById('{element}').getBoundingClientRect();return {{x:r.x,y:r.y,width:r.width,height:r.height}}}})()")
        image=window.pixel_page.view.grab().toImage();scale=image.width()/window.pixel_page.view.width()
        color=image.pixelColor(round((rect['x']+8)*scale),round((rect['y']+8)*scale))
        rgb=[color.red(),color.green(),color.blue()]
        if not all(abs(a-b)<12 for a,b in zip(rgb,[23,37,58])):
            window.grab().save(str(root/'preview-pixel-tile-failure.png'))
        assert all(abs(a-b)<12 for a,b in zip(rgb,[23,37,58])),f"Tile incorreto ao rolar {element}: {rgb}; rect={rect}; scroll={js('window.scrollY')}; render={js('BeatlightPixel.status().render_ms')}"
        checks.append({'control':element,'rgb':rgb})
    js("(scrollTo(0,0),true)");wait_seconds(.2)
    return checks

try:
    pump(lambda:window.pixel_page.bridge.ready_state,20)
    pump(lambda:not window.busy and bool(window.devices))
    project=js("BeatlightPixel.project()")
    validate_project(project)
    assert len(project["strips"])==6
    assert all(s["profile"]=="ws2811" for s in project["strips"])
    assert project['show']['changeMode'] in ('bars','hybrid','elements','hold')
    report['renderer']='software'
    report['scroll_tiles']=check_tiles()
    project["show"].update(mode="ambient",followStructure=True,palette="deep",colorBehavior="scene")
    project["strips"][0].update(palette="red",effect="ambient",response="ambient")
    project["strips"][1].update(palette="blue",effect="wave",response="ambient",phase=.3)
    project["strips"][2]["enabled"]=False
    js("BeatlightPixel.applyProject("+json.dumps(project)+")")
    js("(BeatlightPixel.arm(true),true)")
    dark=js("BeatlightPixel.renderFrame()")
    assert all(not any(s["data"]) for s in dark["strips"])
    window.pixel_page.start.click()
    pump(lambda:window.runtime.snapshot() is not None and window.runtime.status().elapsed>2)
    capture_start=monotonic()-window.runtime.status().elapsed
    frame=validate_frame(js("BeatlightPixel.renderFrame()"))
    red,blue,off=frame["strips"][:3]
    assert any(red["data"][::3]) and not any(red["data"][1::3]) and not any(red["data"][2::3])
    assert any(blue["data"][2::3]) and not any(blue["data"][::3]) and not any(blue["data"][1::3])
    assert not any(off["data"])
    assert all(s["model"]=="RGB" and len(s["data"])==s["pixels"]*3 for s in frame["strips"])
    pump(lambda:window.pixel_page.drop.isEnabled())
    window.pixel_page.drop.click();pump(lambda:window.pixel_page.bridge.operator.get('manualDrop'))
    assert js('BeatlightPixel.status().manualDrop')
    assert 'ENCERRAR' in window.pixel_page.drop.text()
    window.pixel_page.drop.click();pump(lambda:not window.pixel_page.bridge.operator.get('manualDrop'))
    report['native_manual_drop']=True
    js("(BeatlightPixel.blackout(true),true)")
    assert all(not any(s["data"]) for s in js("BeatlightPixel.renderFrame()")["strips"])
    js("(BeatlightPixel.blackout(false),BeatlightPixel.sync(),true)")
    drops=set();first_drop=None
    until=monotonic()+(1 if smoke else 25)
    screenshot=False
    while monotonic()<until:
        app.processEvents()
        status=window.runtime.status();snapshot=window.runtime.snapshot()
        rendered=[event for event in window.pixel_page.bridge.events if event["kind"]=="drop-render"]
        if rendered:
            drops.update(event["count"] for event in rendered)
            if first_drop is None:
                first_drop=rendered[0]["received_at"]-capture_start
            if not screenshot and max(drops)>=3:
                window.grab().save(str(root/"preview-pixel-studio.png"));screenshot=True
        for error in (snapshot.structure_error if snapshot else "",window.last_error):
            if error:report["errors"].append(error)
        sleep(.005)
    report['render_ms']=js('BeatlightPixel.status().render_ms')
    if not smoke:
        assert drops==set(range(1,9)) and first_drop<20.3, f"Kicks={sorted(drops)}, primeiro drop={first_drop}, status={window.runtime.status()}, render={js('BeatlightPixel.status()')}, eventos={list(window.pixel_page.bridge.events)[:4]}"
    else:window.grab().save(str(root/"preview-pixel-studio-smoke.png"))
    window._stop_capture();pump(lambda:not window.busy and window.runtime.status().state=="stopped")
    pump(lambda:all(not any(s["data"]) for s in js("BeatlightPixel.renderFrame()")["strips"]))
    saved=window.pixel_page.bridge.store.load()
    assert saved and saved["strips"][0]["palette"]=="red"
    report.update(ready=True,independent_rgb=True,blackout_zero=True,stop_zero=True,
                  persisted=True,drop_kicks=sorted(drops),first_drop=first_drop,
                  dropped_blocks=window.runtime.status().dropped_blocks)
    # Fechar imediatamente após uma edição também deve preservar o último valor.
    js("(()=>{const p=BeatlightPixel.project();p.strips[0].phase=.123;return BeatlightPixel.applyProject(p)})()")
finally:
    window.close();pump(lambda:window.closed_ready)
    app.processEvents()
report["closed_cleanly"]=window.closed_ready
assert window.pixel_page.bridge.store.load()["strips"][0]["phase"]==.123
report["last_edit_saved_on_close"]=True
(root/"docs"/f"resultado-pixel-studio-v{__version__}{'-smoke' if smoke else ''}.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
assert not report["errors"] and report["dropped_blocks"]==0
