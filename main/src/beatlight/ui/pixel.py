"""Pixel Studio local: Canvas existente + snapshots de música via Qt WebChannel."""
import json
from pathlib import Path
import sysconfig
from time import monotonic
from collections import deque
from PySide6.QtCore import QObject,QUrl,QFile,QIODevice,Signal,Slot,Qt,QCoreApplication,QTimer
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QFileDialog,QSizePolicy
from beatlight.pixel.project import PixelProjectStore,MAX_BYTES
from beatlight.pixel.protocol import music_packet,validate_frame
from beatlight.pixel.rendering import configure_renderer
from beatlight.ui.pixel_usb import PixelUsbPanel

RENDERER=configure_renderer()

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

    def __init__(self,store,parent=None):
        super().__init__(parent)
        self.store=store
        self.ready_state=False
        self.last_frame=None
        self.events=deque(maxlen=64)
        self.operator={}

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
    def ready(self):
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
            if len(payload)>MAX_BYTES:raise ValueError("Projeto excede 500 KB.")
            self.store.save(json.loads(payload))
            self.notice.emit("Projeto de fitas salvo automaticamente.")
        except (OSError,ValueError,TypeError,KeyError) as exc:
            self.notice.emit(f"Projeto não salvo: {exc}")

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
    def __init__(self,owner):
        super().__init__(owner)
        self.owner=owner
        self.view=None
        self.load_events=[]
        self.shutting_down=False
        self._web_closed=True
        self.bridge=PixelBridge(PixelProjectStore(owner.store.path.parent/"pixel-studio.json"),self)
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
        self.usb=PixelUsbPanel(self);self.layout_box.addWidget(self.usb)
        self.placeholder=QLabel("Pixel Studio · abrindo o simulador local…")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout_box.addWidget(self.placeholder,1)
        self.notice=QLabel("Prévia de pixels · saída física WS2812 disponível no painel ESP32 USB.")
        self.notice.setWordWrap(True); self.notice.setFixedHeight(32)
        self.layout_box.addWidget(self.notice)
        self.bridge.notice.connect(self.notice.setText)

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
                        self.notice.setText(f"Pixel Studio: {message}")
            self.profile=QWebEngineProfile(self)
            self.interceptor=LocalOnly(self.profile); self.profile.setUrlRequestInterceptor(self.interceptor)
            self.profile.downloadRequested.connect(self._download)
            self.view=QWebEngineView(self)
            self.webpage=Page(self.profile,self.view); self.view.setPage(self.webpage)
            self.webpage.loadingChanged.connect(lambda info:self.load_events.append((str(info.status()),info.errorCode(),info.errorString(),info.url().toString()[:200])))
            self.webpage.loadingChanged.connect(lambda info:self.notice.setText("Pixel Studio: "+info.errorString()) if info.errorCode() else None)
            self.webpage.renderProcessTerminated.connect(lambda status,code:self.usb.fail(f"Renderizador Pixel Studio encerrou: {status}, {code}"))
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

    def _fullscreen(self,request):
        request.accept()
        self.owner.showFullScreen() if request.toggleOn() else self.owner.showNormal()

    def _manual_drop(self):
        if self.view and self.bridge.ready_state:
            self.webpage.runJavaScript("BeatlightPixel.manualDrop()")

    def _download(self,request):
        path,_=QFileDialog.getSaveFileName(self,"Exportar Pixel Studio",request.suggestedFileName(),"JSON (*.json)")
        if path:
            target=Path(path); request.setDownloadDirectory(str(target.parent)); request.setDownloadFileName(target.name); request.accept()
        else:request.cancel()

    def update_music(self,snapshot,status,at):
        self.start.setEnabled(self.owner.start_button.isEnabled()); self.stop.setEnabled(self.owner.stop_button.isEnabled())
        self.drop.setEnabled(self.bridge.ready_state and not self.owner.closing and not self.bridge.operator.get("blackout",False)
            and (self.bridge.operator.get("source")=="demo" or status.state=="running" and status.audio_age<.5))
        self.status.setText(("Áudio ativo" if status.state=="running" else "Áudio parado")+
                            (" · relógio Link" if snapshot and snapshot.timing_source=="link" else " · grade acústica"))
        if self.bridge.ready_state:
            self.bridge.packet.emit(json.dumps(music_packet(snapshot,status,at),allow_nan=False,separators=(",",":")))

    @property
    def closed_ready(self):return self._web_closed and self.usb.runtime.closed

    def shutdown(self):
        self.usb.shutdown()
        if self.view and not self.shutting_down:
            self.shutting_down=True
            self._web_closed=False
            self.bridge.ready_state=False
            def cleanup():
                if self._web_closed:return
                self._web_closed=True
                self.webpage.deleteLater();self.profile.deleteLater()
            def saved(payload):
                if self._web_closed:return
                try:
                    if payload:self.bridge.store.save(json.loads(payload))
                except (OSError,ValueError,TypeError) as exc:
                    self.notice.setText(f"Último ajuste não salvo: {exc}")
                cleanup()
            self.webpage.runJavaScript("globalThis.BeatlightPixel?JSON.stringify((BeatlightPixel.shutdown(),BeatlightPixel.project())):''",saved)
            QTimer.singleShot(1000,cleanup)
