"""Pixel Studio local: Canvas existente + snapshots de música via Qt WebChannel."""
import json
from pathlib import Path
import sysconfig
from time import monotonic
from collections import deque
from PySide6.QtCore import QObject,QUrl,QFile,QIODevice,Signal,Slot,Qt,QCoreApplication,QTimer,QEvent
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QFileDialog,QSizePolicy
from beatlight.pixel.project import PixelProjectStore,MAX_BYTES
from beatlight.pixel.project_writer import LatestProjectWriter
from beatlight.pixel.protocol import music_packet,validate_frame
from beatlight.pixel.rendering import configure_renderer
from beatlight.ui.pixel_usb import PixelUsbPanel

RENDERER=configure_renderer()

# Native Windows file dialogs stop QTimers, including the USB frame producer.
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs)

if QCoreApplication.instance() is None:
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)


def studio_asset():
    candidates=[Path(__file__).resolve().parents[3]/"beatlight"/"beatlight_pixel_studio.html",
                Path(sysconfig.get_path("data"))/"share"/"beatlight"/"beatlight_pixel_studio.html"]
    return next((p for p in candidates if p.is_file()),candidates[0])


class PixelBridge(QObject):
    packet=Signal(str)
    project=Signal(str)
    notice=Signal(str)
    connected=Signal()
    operatorChanged=Signal()
    previewRequested=Signal()
    controlsChanged=Signal()
    fullscreenRequested=Signal()

    @Slot()
    def toggleFullscreen(self):self.fullscreenRequested.emit()

    def __init__(self,store,parent=None):
        super().__init__(parent)
        self.store=store
        self.writer=LatestProjectWriter(store,self.notice.emit)
        self.ready_state=False
        self.last_frame=None
        self.events=deque(maxlen=64)
        self.operator={}
        self.controls={}
        self._music_pending=None;self._music_inflight=None;self._music_serial=0
        self.music_coalesced=0

    @Slot(str)
    def operatorState(self,payload):
        try:
            if len(payload)>256:return
            data=json.loads(payload)
            if not isinstance(data,dict) or data.get("source") not in ("live","demo"):return
            if any(type(data.get(k)) is not bool for k in ("armed","blackout","manualDrop")):return
            self.operator=data
            self.operatorChanged.emit()
        except ValueError:pass

    @Slot()
    def requestPreview(self):
        self.previewRequested.emit()

    @Slot(str)
    def controlState(self,payload):
        try:
            if not isinstance(payload,str) or len(payload)>512:return
            data=json.loads(payload)
            if not isinstance(data,dict) or data.get('manual_structure') not in (None,'groove','breakdown','buildup'):return
            if data.get('structure') not in ('warming','groove','breakdown','buildup','drop','silence'):return
            if not isinstance(data.get('mode'),str) or len(data['mode'])>32:return
            if any(type(data.get(key)) is not bool for key in ('drop','continuous','queued','sync')):return
            if 'cue_sync' in data and type(data['cue_sync']) is not bool:return
            if type(data.get('peak_level')) not in (float,int) or not 0<=data['peak_level']<=1:return
            self.controls=data;self.controlsChanged.emit()
        except (ValueError,TypeError):pass

    @Slot()
    def ready(self):
        self._music_pending=self._music_inflight=None
        try:
            data=self.store.load()
            self.project.emit(json.dumps(data,ensure_ascii=False,allow_nan=False))
        except (OSError,ValueError,TypeError,KeyError) as exc:
            self.notice.emit(f"Projeto anterior indisponível; modelo inicial mantido: {exc}")
            self.project.emit("null")
        self.ready_state=True
        self.connected.emit()

    @Slot(str)
    def saveProject(self,payload):
        try:
            self.writer.submit(payload)
        except (OSError,ValueError,TypeError,KeyError,RuntimeError) as exc:
            self.notice.emit(f"Projeto não salvo: {exc}")

    def send_music(self,packet):
        if self._music_inflight is not None:
            self._music_pending=packet;self.music_coalesced+=1;return
        self._music_serial=self._music_serial%2_147_483_647+1;self._music_inflight=self._music_serial
        self.packet.emit(json.dumps({**packet,'delivery_id':self._music_serial},allow_nan=False,separators=(',',':')))

    @Slot(int)
    def musicConsumed(self,delivery_id):
        if delivery_id!=self._music_inflight:return
        self._music_inflight=None
        pending=self._music_pending;self._music_pending=None
        if pending is not None and self.ready_state:self.send_music(pending)

    @Slot(str)
    def pixelEvent(self,payload):
        try:
            if len(payload)>256:return
            event=json.loads(payload)
            if event.get("kind") in ("drop-kick","drop-render") and type(event.get("count")) is int and 1<=event["count"]<=8:
                self.events.append({**event,"received_at":monotonic()})
        except (ValueError,AttributeError):pass

    @Slot(str)
    def publishFrame(self,payload):
        try:
            if len(payload)>500_000:raise ValueError("Quadro muito grande.")
            self.last_frame=validate_frame(json.loads(payload))
        except (ValueError,TypeError,KeyError) as exc:
            self.notice.emit(f"Quadro RGB inválido: {exc}")


class PixelStudioPage(QWidget):
    commandRejected=Signal(str)
    def __init__(self,owner):
        super().__init__(owner)
        self.owner=owner
        self.view=None
        self.load_events=deque(maxlen=128)
        self.render_errors=deque(maxlen=32)
        self.shutting_down=False
        self._web_closed=True
        self._reloading=False
        self._render_context=None
        self._fullscreen_state=None
        self._control_commands=deque();self._control_busy=False;self._control_serial=0;self.control_blocked=False
        self.bridge=PixelBridge(PixelProjectStore(owner.store.path.parent/"pixel-studio.json"),self)
        self.bridge.fullscreenRequested.connect(self.toggle_fullscreen)
        QCoreApplication.instance().installEventFilter(self)
        self.layout_box=QVBoxLayout(self); self.layout_box.setContentsMargins(0,0,0,0)
        row=QHBoxLayout()
        self.start=QPushButton("▶ Iniciar áudio")
        self.stop=QPushButton("■ Parar áudio")
        self.start.clicked.connect(owner._start); self.stop.clicked.connect(owner._stop_capture)
        row.addWidget(self.start); row.addWidget(self.stop)
        self.drop=QPushButton("⚡ DROP AGORA")
        self.drop.setStyleSheet("QPushButton {background:#a94719;color:#ffffff;border:2px solid #ffad55;font-weight:800;padding:9px 16px;} QPushButton:hover {background:#cf6028;} QPushButton:disabled {background:#493225;color:#ad9789;}")
        self.drop.setToolTip("Disparar drop agora por oito tempos. Durante o drop manual, clique para encerrar. Atalho: D no simulador.")
        self.drop.clicked.connect(self._manual_drop)
        row.addWidget(self.drop)
        self.bridge.operatorChanged.connect(lambda:self.drop.setText("■ ENCERRAR DROP" if self.bridge.operator.get("manualDrop") else "⚡ DROP AGORA"))
        for text,index in (("Selecionar entrada",0),("Ableton Link",8)):
            button=QPushButton(text); button.clicked.connect(lambda checked=False,i=index:owner._navigate(i)); row.addWidget(button)
        self.status=QLabel("Fitas independentes · sincronização pela análise de áudio e Link")
        self.status.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        row.addWidget(self.status,1); self.layout_box.addLayout(row)
        self.fullscreen_button=QPushButton('Tela cheia · F11');self.fullscreen_button.clicked.connect(self.toggle_fullscreen);row.addWidget(self.fullscreen_button)
        self.logs_button=QPushButton('Logs da saída');self.logs_button.clicked.connect(self.show_output_logs);row.addWidget(self.logs_button)
        self._log_dialog=None
        self.usb=PixelUsbPanel(self);self.layout_box.addWidget(self.usb)
        self.placeholder=QLabel("Pixel Studio · abrindo o simulador local…")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout_box.addWidget(self.placeholder,1)
        self.notice=QLabel("Prévia de pixels · saída física WS2812 disponível no painel ESP32 USB.")
        self.notice.setWordWrap(True); self.notice.setFixedHeight(32)
        self.layout_box.addWidget(self.notice)
        self.bridge.notice.connect(self.notice.setText)
        self.bridge.connected.connect(lambda:setattr(self,'_render_context',None))
        self.bridge.connected.connect(self._reset_commands)

    def _reset_commands(self):
        self._control_serial+=1;self._control_busy=False;self.control_blocked=False;self._control_commands.clear()

    def queue_controls(self,commands):
        if self.shutting_down or not self.bridge.ready_state or self.control_blocked:return False
        from beatlight.midi.mapping import ACTIONS
        for action,value in commands:
            if not isinstance(action,str):return False
            if action not in ACTIONS and action!='release_structure':return False
            if action=='peak_level':
                if type(value) not in (int,float) or not 0<=value<=1:return False
                self._control_commands=deque(item for item in self._control_commands if item[0]!='peak_level')
            if len(self._control_commands)>=64:
                self.notice.setText('Comandos MIDI excederam o limite; aguarde a prévia.');return False
            self._control_commands.append((action,value))
        self._flush_commands();return True

    def _flush_commands(self):
        if self._control_busy or not self._control_commands or not self.bridge.ready_state or self.control_blocked:return
        commands=list(self._control_commands);self._control_commands.clear();self._control_busy=True;self._control_serial+=1;serial=self._control_serial
        expression='BeatlightPixel.controlBatch('+json.dumps(commands)+','+str(monotonic())+')'
        def completed(result):
            if serial!=self._control_serial:return
            if result is False:self.commandRejected.emit('Um comando MIDI não foi aplicado. Confira áudio/grade e aguarde o final do drop para trocar combinações.')
            self._control_busy=False;self._flush_commands()
        def expired():
            if serial!=self._control_serial or not self._control_busy:return
            self.control_blocked=True;self._control_serial+=1;self._control_commands.clear();self._control_busy=False
            self.notice.setText('A prévia não respondeu aos comandos. Reabra a prévia para retomar o controle MIDI.')
        self.webpage.runJavaScript(expression,completed);QTimer.singleShot(500,expired)

    def ensure_loaded(self):
        if self.view is not None:return
        try:
            from PySide6.QtWebChannel import QWebChannel
            from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile,QWebEngineScript,QWebEngineUrlRequestInterceptor,QWebEngineSettings
            from PySide6.QtWebEngineWidgets import QWebEngineView
            asset=studio_asset()
            if not asset.is_file():raise OSError(f"Arquivo Pixel Studio ausente: {asset}")
            events=self.load_events
            class LocalOnly(QWebEngineUrlRequestInterceptor):
                def interceptRequest(self,info):
                    url=info.requestUrl()
                    allowed=url.scheme() in ("qrc","data","blob","about")
                    if url.isLocalFile():
                        allowed=Path(url.toLocalFile()).resolve()==asset.resolve()
                    if not allowed:events.append(("blocked",url.toString()[:200]))
                    if not allowed:info.block(True)
            class Page(QWebEnginePage):
                def acceptNavigationRequest(self,url,kind,main):
                    allowed=url.scheme() in ("about","blob","data") or url.isLocalFile() and Path(url.toLocalFile()).resolve()==asset.resolve()
                    events.append(("navigation",url.scheme(),bool(allowed),url.toString()[:150]))
                    return allowed
                def javaScriptConsoleMessage(page,level,message,line,source):
                    if level==QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
                        self.render_errors.append((line,message[:1000]))
                        self.notice.setText(f"Pixel Studio: {message}")
            self.profile=QWebEngineProfile(self)
            self.interceptor=LocalOnly(self.profile); self.profile.setUrlRequestInterceptor(self.interceptor)
            self.profile.downloadRequested.connect(self._download)
            self.view=QWebEngineView(self)
            self.webpage=Page(self.profile,self.view); self.view.setPage(self.webpage)
            self.webpage.loadingChanged.connect(lambda info:self.load_events.append((str(info.status()),info.errorCode(),info.errorString(),info.url().toString()[:200])))
            self.webpage.loadingChanged.connect(lambda info:self.notice.setText("Pixel Studio: "+info.errorString()) if info.errorCode() else None)
            self.webpage.renderProcessTerminated.connect(self._renderer_failed)
            self.webpage.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled,True)
            if RENDERER=="software":
                self.webpage.settings().setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled,False)
                self.webpage.settings().setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled,False)
            from PySide6.QtGui import QColor
            self.webpage.setBackgroundColor(QColor("#0c1119"))
            self.webpage.fullScreenRequested.connect(self._fullscreen)
            self.channel=QWebChannel(self.webpage); self.channel.registerObject("beatlight",self.bridge)
            self.webpage.setWebChannel(self.channel)
            resource=QFile(":/qtwebchannel/qwebchannel.js")
            if not resource.open(QIODevice.OpenModeFlag.ReadOnly):raise OSError("Qt WebChannel indisponível.")
            source=bytes(resource.readAll()).decode("utf-8"); resource.close()
            script=QWebEngineScript(); script.setName("beatlight-local-bridge")
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            script.setSourceCode("globalThis.__BEATLIGHT_EMBEDDED__=true;\n"+source)
            self.webpage.scripts().insert(script)
            self.view.loadFinished.connect(self._loaded)
            self.layout_box.replaceWidget(self.placeholder,self.view); self.placeholder.deleteLater()
            self.view.setHtml(asset.read_text(encoding="utf-8"),QUrl.fromLocalFile(str(asset)))
        except (ImportError,OSError) as exc:
            self.notice.setText(f"Não foi possível abrir o Pixel Studio: {exc}")

    def _loaded(self,ok):
        if not ok:
            if not self.notice.text().startswith("Pixel Studio:"):
                self.notice.setText("Falha ao carregar o simulador local.")
            return
        self.webpage.runJavaScript("new QWebChannel(qt.webChannelTransport,c=>BeatlightPixel.attachBridge(c.objects.beatlight));")

    def _renderer_failed(self,status,code):
        self.exit_fullscreen()
        self._reset_commands();self.control_blocked=True;self.bridge.controls={};self.bridge.controlsChanged.emit()
        self.usb.fail(f'Renderizador Pixel Studio encerrou: {status}, {code}')

    def _fullscreen(self,request):
        # Canvas-only Chromium fullscreen hides every exit control. Keep the
        # native window and its exit button in charge, including old requests.
        request.reject()
        self.toggle_fullscreen() if request.toggleOn() and not self.owner.isFullScreen() else self.exit_fullscreen() if not request.toggleOn() else None

    def toggle_fullscreen(self):
        if self.owner.isFullScreen():self.exit_fullscreen();return
        if self.owner.closing:return
        self._fullscreen_state=self.owner.windowState()
        self.owner.showFullScreen();self.fullscreen_button.setText('Sair da tela cheia · Esc')
        self.owner.sidebar.setVisible(False)

    def exit_fullscreen(self):
        if self._fullscreen_state is None and not self.owner.isFullScreen():return
        previous=self._fullscreen_state;self._fullscreen_state=None
        self.owner.setWindowState(previous if previous is not None else Qt.WindowState.WindowNoState)
        self.owner.sidebar.setVisible(True);self.fullscreen_button.setText('Tela cheia · F11')

    def eventFilter(self,watched,event):
        if event.type() not in (QEvent.Type.KeyPress,QEvent.Type.ShortcutOverride):return False
        if self.owner.pages.currentIndex()!=9 or self.owner.closing:return False
        if QApplication.activeWindow() not in (None,self.owner):return False
        key=event.key()
        if key==Qt.Key.Key_F11 or key==Qt.Key.Key_Escape and self.owner.isFullScreen():
            if event.type()==QEvent.Type.KeyPress and not event.isAutoRepeat():
                self.toggle_fullscreen() if key==Qt.Key.Key_F11 else self.exit_fullscreen()
            event.accept();return True
        return False

    def show_output_logs(self):
        from beatlight.ui.output_log import OutputLogDialog
        if self._log_dialog is None:self._log_dialog=OutputLogDialog(self.owner.output_journal,self)
        self._log_dialog.show();self._log_dialog.raise_();self._log_dialog.activateWindow()

    def _manual_drop(self):
        if self.view and self.bridge.ready_state:
            self.webpage.runJavaScript("BeatlightPixel.manualDrop()")

    def reload_preview(self):
        if self.owner.closing or self._reloading or not self.view:return
        self.exit_fullscreen()
        self._reloading=True;self.usb._off('preview_reload','Prévia recarregada pelo operador; saída física desativada.');self.bridge.ready_state=False
        self.bridge.controls={};self.bridge.controlsChanged.emit()
        self._reset_commands()
        self.bridge._music_pending=self.bridge._music_inflight=None
        self.notice.setText('Reabrindo a prévia; áudio continua ativo e a saída USB fica apagada.')
        launched=False
        def launch():
            nonlocal launched
            if launched or self.owner.closing:return
            launched=True;self._reloading=False
            try:
                asset=studio_asset();self.view.setHtml(asset.read_text(encoding='utf-8'),QUrl.fromLocalFile(str(asset)))
            except OSError as exc:self.notice.setText(f'Não foi possível reabrir a prévia: {exc}')
        def wait_writer():
            if self.bridge.writer.busy or self.bridge.writer.pending:QTimer.singleShot(25,wait_writer)
            else:launch()
        def saved(payload):
            if launched or self.owner.closing:return
            try:
                if payload:self.bridge.writer.submit(payload)
            except (ValueError,RuntimeError) as exc:self.notice.setText(str(exc))
            wait_writer()
        self.webpage.runJavaScript('globalThis.BeatlightPixel?JSON.stringify(BeatlightPixel.persistedProject()):""',saved)
        # A dead renderer cannot return its last edit: recover the last valid file.
        QTimer.singleShot(1000,wait_writer)

    def _download(self,request):
        path,_=QFileDialog.getSaveFileName(self,"Exportar Pixel Studio",request.suggestedFileName(),"JSON (*.json)")
        if path:
            target=Path(path); request.setDownloadDirectory(str(target.parent)); request.setDownloadFileName(target.name); request.accept()
        else:request.cancel()

    def set_render_context(self,visible,low_power=False):
        context=(bool(visible),bool(low_power))
        if self.bridge.ready_state and context!=self._render_context:
            self._render_context=context
            self.webpage.runJavaScript('BeatlightPixel.setRenderPolicy('+','.join(str(value).lower() for value in context)+')')

    def update_music(self,snapshot,status,at,paint=True):
        if paint:
            self.start.setEnabled(self.owner.start_button.isEnabled()); self.stop.setEnabled(self.owner.stop_button.isEnabled())
            self.drop.setEnabled(self.bridge.ready_state and not self.owner.closing and not self.bridge.operator.get("blackout",False)
                and (self.bridge.operator.get("source")=="demo" or status.state=="running" and status.audio_age<.5))
            self.status.setText(("Áudio ativo" if status.state=="running" else "Áudio parado")+
                                (" · relógio Link" if snapshot and snapshot.timing_source=="link" else " · grade acústica"))
        if self.bridge.ready_state:
            self.bridge.send_music(music_packet(snapshot,status,at))

    @property
    def closed_ready(self):return self._web_closed and self.usb.runtime.closed and self.bridge.writer.closed

    def shutdown(self):
        self.exit_fullscreen()
        QCoreApplication.instance().removeEventFilter(self)
        self._reset_commands()
        self.usb.shutdown()
        if self.view and not self.shutting_down:
            self.shutting_down=True
            self._web_closed=False
            self.bridge.ready_state=False
            def cleanup():
                if self._web_closed:return
                self.bridge.writer.close()
                self._web_closed=True
                self.webpage.deleteLater();self.profile.deleteLater()
            def saved(payload):
                if self._web_closed:return
                try:
                    if payload:self.bridge.writer.submit(payload)
                except (OSError,ValueError,TypeError,RuntimeError) as exc:
                    self.notice.setText(f"Último ajuste não salvo: {exc}")
                cleanup()
            self.webpage.runJavaScript("globalThis.BeatlightPixel?JSON.stringify((BeatlightPixel.shutdown(),BeatlightPixel.persistedProject())):''",saved)
            QTimer.singleShot(1000,cleanup)
        elif self.view is None:self.bridge.writer.close()
