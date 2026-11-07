"""Layout real, retorno de tela cheia e composição íntegra; sem hardware."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu --disable-gpu-compositing --no-sandbox')
from pathlib import Path
from time import monotonic,sleep
import json,tempfile
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from beatlight import __version__
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.ui.window import MainWindow
from beatlight.ui.theme import STYLE
import beatlight.ui.pixel as pixel_ui
root=Path(__file__).resolve().parents[1];app=QApplication([]);app.setStyle('Fusion');app.setStyleSheet(STYLE)
for name in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
report=dict(version=__version__,physical_device_used=False,layouts=[],copy_checks=0)
with tempfile.TemporaryDirectory(prefix='workspace-',dir=root/'.runtime') as folder:
    asset=Path(folder)/'studio.html';source=(root/'beatlight/beatlight_pixel_studio.html').read_text(encoding='utf-8')
    source=source.replace('    globalThis.BeatlightPixel={','    globalThis.qaPresentFull=()=>presentFrame(true);\n    globalThis.BeatlightPixel={',1)
    asset.write_text(source,encoding='utf-8');pixel_ui.studio_asset=lambda:asset
    window=MainWindow(SettingsStore(Path(folder)/'preferences.json'),Settings(source='synthetic'));window.show();window._navigate(9)
    def pump(condition,timeout=15):
        end=monotonic()+timeout
        while monotonic()<end:
            app.processEvents()
            if condition():return
            sleep(.003)
        assert condition(),(window.pixel_page.notice.text(),list(window.pixel_page.render_errors))
    def js(expression):
        result=[];window.pixel_page.webpage.runJavaScript('JSON.stringify('+expression+')',result.append);pump(lambda:bool(result));return json.loads(result[0])
    def settle():
        start=monotonic();pump(lambda:monotonic()-start>.35)
    def rects():
        return js('(()=>{const r=document.getElementById("stage").getBoundingClientRect(),p=document.getElementById("inspector").getBoundingClientRect();return {stage:[r.x,r.y,r.width,r.height],panel:[p.x,p.y,p.width,p.height],viewport:[innerWidth,innerHeight],scroll:[document.documentElement.scrollWidth,document.documentElement.scrollHeight]}})()')
    def screenshot(label):assert window.grab().save(str(root/f'preview-workspace-{label}-v{__version__}.png'))
    try:
        pump(lambda:window.pixel_page.bridge.ready_state and not window.busy);window.timer.stop()
        js('(BeatlightPixel.previewProject(),true)');settle()
        for area in ('stage','effects','layout','library'):
            js('(BeatlightPixel.setWorkspace('+json.dumps(area)+'),true)');settle();data=rects()
            x,y,width,height=data['stage'];vw,vh=data['viewport']
            assert x>=0 and y>=0 and width>=200 and height>=140 and x+width<=vw+1 and y+height<=vh+1,data
            assert data['scroll'][0]<=vw+1 and data['scroll'][1]<=vh+1,data
            if area!='stage':assert data['panel'][0]>=x+width-1,data
            report['layouts'].append(dict(area=area,**data));screenshot(area)
        js('(BeatlightPixel.setWorkspace("stage"),true)');window.showMaximized();settle()
        for exit_method in ('escape','f11','button'):
            window.pixel_page.view.setFocus();QTest.keyClick(window.pixel_page.view,Qt.Key.Key_F11);pump(window.isFullScreen)
            assert not window.sidebar.isVisible();settle()
            if exit_method=='button':window.pixel_page.fullscreen_button.click()
            else:QTest.keyClick(window.pixel_page.view,Qt.Key.Key_Escape if exit_method=='escape' else Qt.Key.Key_F11)
            pump(lambda:not window.isFullScreen());assert window.isMaximized() and window.sidebar.isVisible()
        report['fullscreen_escape_f11_button']=True
        # Freeze clock advancement so full and incremental copies compare the
        # same completed back buffer, including rotated strips and flash decay.
        for angle in (False,True):
            js('(()=>{const p=BeatlightPixel.project();p.show.strobes=true;p.show.strobeMode="beat";'+('p.geometry.lines.forEach((l,i)=>{l.end.x=100+i*170;l.end.y=120+i*20;l.start.x=100+i*170+110});' if angle else '')+'BeatlightPixel.applyProject(p);return true})()')
            for _ in range(6):
                settle()
                equal=js('(()=>{const c=document.getElementById("stage"),ctx=c.getContext("2d"),a=ctx.getImageData(0,0,c.width,c.height).data;qaPresentFull();const b=ctx.getImageData(0,0,c.width,c.height).data;return a.every((v,i)=>v===b[i])})()')
                assert equal;report['copy_checks']+=1
        report['complete_frame_parity']=True
        window.resize(1100,760);window.showNormal();settle();js('(BeatlightPixel.setWorkspace("effects"),true)');settle()
        js('(BeatlightPixel.setEffectMix("single"),BeatlightPixel.markCueReference(),document.getElementById("singleRulesFold").open=true,true)');settle()
        data=rects();assert data['stage'][2]>=200 and data['stage'][3]>=140 and data['scroll'][0]<=data['viewport'][0]+1 and data['scroll'][1]<=data['viewport'][1]+1,data
        assert js('document.querySelectorAll("#singleRules .single-rule").length')==39
        report['single_repertoire_and_reference_visible']=True
        assert js('document.getElementById("cueSync").getAttribute("aria-pressed")')=='true'
        js('(document.getElementById("cueSync").click(),true)')
        assert js('BeatlightPixel.status().reference.origin') is None
        assert js('document.getElementById("cueSync").getAttribute("aria-pressed")')=='false'
        js('(document.getElementById("cueSync").click(),true)')
        assert js('BeatlightPixel.status().reference.origin') is not None
        report['reference_button_toggles_off_and_on']=True
        js('(document.getElementById("quickManual").click(),true)');settle()
        assert js('BeatlightPixel.status().manual.active')
        manual_before=js('BeatlightPixel.status().manual.pattern')
        js('(document.getElementById("manualNext").click(),true)');assert js('BeatlightPixel.status().manual.pattern')!=manual_before
        js('(document.getElementById("manualPrevious").click(),true)');assert js('BeatlightPixel.status().manual.pattern')==manual_before
        nav=js('(()=>{const r=document.getElementById("manualNav").getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom,viewport:innerHeight}})()')
        assert nav['width']>250 and nav['height']>0 and nav['bottom']<=nav['viewport']+1,nav
        data=rects();assert data['stage'][3]>=140 and data['scroll'][1]<=data['viewport'][1]+1,data
        report['manual_navigation_visible_compact']=nav;screenshot('manual-compact')
        js('(document.getElementById("quickAuto").click(),true)');assert not js('BeatlightPixel.status().manual.active')
        report['minimum_window_layout']=data;screenshot('compact')
        window.pixel_page.toggle_fullscreen();window.pixel_page.reload_preview();pump(lambda:window.pixel_page.bridge.ready_state and not window.pixel_page._reloading)
        assert not window.isFullScreen();report['reload_exits_fullscreen']=True
        report['errors']=list(window.pixel_page.render_errors);assert not report['errors'];report['passed']=True
    finally:
        window.timer.start();window.close();pump(lambda:window.closed_ready)
report['closed_cleanly']=True
(root/'docs'/f'resultado-pixel-workspace-v{__version__}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
