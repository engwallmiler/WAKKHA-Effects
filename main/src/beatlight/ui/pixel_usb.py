"""Controles de uma fita física WS2812, separados do desenho da prévia."""
import json
import os
import sysconfig
from pathlib import Path
import tempfile
from threading import Thread
from time import monotonic
from PySide6.QtCore import QTimer,Signal,QUrl
from PySide6.QtWidgets import (QWidget,QGroupBox,QGridLayout,QHBoxLayout,QVBoxLayout,
    QComboBox,QPushButton,QLabel,QSpinBox,QDialog,QDialogButtonBox,QTextBrowser)
from beatlight.pixel.usb import PixelUsbOutput,list_ports
from beatlight.pixel.usb_protocol import OutputConfig,rgb_payload


class PixelUsbPanel(QWidget):
    portsReady=Signal(object,str)

    def __init__(self,page,runtime=None):
        super().__init__(page)
        self.page=page;self.runtime=runtime or PixelUsbOutput()
        self.path=page.owner.store.path.parent/'pixel-usb.json'
        self.closing=False;self.pending=False;self.generation=0
        self.preview_only=True
        self.request_at=0;self.last_sources=-10;self.last_status=-10;self.reading_sources=False
        self.error='';self.desired_id='';saved={}
        try:
            if self.path.exists() and self.path.stat().st_size<4096:
                saved=json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(saved,dict):saved={}
                OutputConfig(saved.get('brightness',64),saved.get('milliamps',2000))
                self.desired_id=saved.get('strip_id','') if isinstance(saved.get('strip_id',''),str) else ''
        except (OSError,ValueError,TypeError):saved={}
        outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0)
        header=QHBoxLayout();self.fold=QPushButton('▸ ESP32 USB · configuração da fita');self.fold.setCheckable(True)
        header.addWidget(self.fold,1);outer.addLayout(header)
        self.mode=QComboBox();self.mode.addItem('Simular projeto atual · sem USB',True);self.mode.addItem('Saída física · ESP32 USB',False)
        self.mode.setToolTip('Simular usa o projeto existente, incluindo barras e grupos, e bloqueia conexão e quadros USB. A fonte pode ser áudio/Link ou demonstração.')
        header.insertWidget(0,self.mode)
        self.mode.currentIndexChanged.connect(lambda:self.set_preview_only(self.mode.currentData()))
        box=QGroupBox('Saída física · ESP32 USB · 1 fita WS2812 / 300 LEDs individuais')
        self.controls_box=box;box.setVisible(False)
        self.fold.toggled.connect(lambda opened:(box.setVisible(opened),self.fold.setText(('▾' if opened else '▸')+' ESP32 USB · configuração da fita')))
        grid=QGridLayout(box);grid.setContentsMargins(10,6,10,8);grid.setHorizontalSpacing(8)
        self.port=QComboBox();self.port.setMinimumWidth(150)
        self.refresh=QPushButton('↻ Portas');self.refresh.clicked.connect(self._scan)
        self.connect_button=QPushButton('Conectar ESP32');self.connect_button.clicked.connect(self._connect)
        self.source=QComboBox();self.source.setMinimumWidth(150);self.source.currentIndexChanged.connect(self._source_changed)
        self.source.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);self.source.setMinimumContentsLength(12)
        self.prepare=QPushButton('Preparar 300 WS2812');self.prepare.clicked.connect(self._prepare)
        self.enable=QPushButton('Ativar saída física');self.enable.setCheckable(True);self.enable.clicked.connect(self._arm)
        self.enable.setStyleSheet('QPushButton:checked {background:#1b684e;border:2px solid #59e1af;color:white;}')
        self.off=QPushButton('APAGAR SAÍDA');self.off.clicked.connect(self._off)
        self.off.setStyleSheet('QPushButton {background:#6f2929;color:white;border:1px solid #df7770;font-weight:800;}')
        header.addWidget(self.enable);header.addWidget(self.off)
        self.reload=QPushButton('Reabrir prévia');self.reload.clicked.connect(page.reload_preview);header.addWidget(self.reload)
        for column,widget in enumerate((self.port,self.refresh,self.connect_button,self.source,self.prepare)):
            grid.addWidget(widget,0,column)
        limits=QHBoxLayout();limits.setContentsMargins(0,0,0,0)
        limits.addWidget(QLabel('Teto de brilho'))
        self.brightness=QSpinBox();self.brightness.setRange(0,100);self.brightness.setSuffix('%');self.brightness.setValue(round(saved.get('brightness',64)*100/255));limits.addWidget(self.brightness)
        limits.addWidget(QLabel('Limite estimado'))
        self.current=QSpinBox();self.current.setRange(500,20000);self.current.setSingleStep(500);self.current.setSuffix(' mA');self.current.setValue(saved.get('milliamps',2000));limits.addWidget(self.current)
        limits.addWidget(QLabel('5 V externos · GND comum · conversor 3,3 → 5 V · GPIO 18'),1)
        self.guide=QPushButton('Instruções');self.guide.clicked.connect(self._guide);limits.addWidget(self.guide)
        grid.addLayout(limits,1,0,1,5)
        self.status=QLabel('Desconectado · use fonte externa de 5 V para a fita, nunca o USB do ESP32.');self.status.setWordWrap(True)
        outer.addWidget(box);outer.addWidget(self.status);self.status.setFixedHeight(28)
        self.portsReady.connect(self._ports_ready)
        self.timer=QTimer(self);self.timer.setInterval(33);self.timer.timeout.connect(self._tick);self.timer.start()
        self.page.bridge.operatorChanged.connect(self._operator_changed)
        self.page.bridge.previewRequested.connect(lambda:self.mode.setCurrentIndex(0))
        self.page.bridge.connected.connect(self._bridge_ready)
        self.source_request_at=0;self.source_timeout=False
        self.sources_payload=None
        self.saved_port=saved.get('port','') if isinstance(saved.get('port',''),str) else ''
        self._scan();self._tick()

    def set_preview_only(self,preview_only):
        self.preview_only=bool(preview_only)
        self.last_status=-10
        if self.preview_only:
            self._off()
            if not self.runtime.closed:self.runtime.disconnect()
        self.timer.setInterval(250 if self.preview_only else 33)
        if self.page.bridge.ready_state:
            self.page.webpage.runJavaScript('BeatlightPixel.setHostOutput('+str(self.preview_only).lower()+')')
        self.fold.setEnabled(not self.preview_only)
        self.fold.setChecked(not self.preview_only)
        self._tick()

    def _save(self):
        temporary=None
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            config=self._config()
            data={'version':1,'port':self.port.currentData() or '', 'strip_id':self.source.currentData() or '',
                  'brightness':config.brightness,'milliamps':config.milliamps}
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=self.path.parent,suffix='.tmp',delete=False) as stream:
                temporary=Path(stream.name);json.dump(data,stream,ensure_ascii=False);stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,self.path)
        except (OSError,ValueError) as exc:self.error=f'Ajustes USB não salvos: {exc}'
        finally:
            if temporary and temporary.exists():temporary.unlink()

    def _config(self):return OutputConfig(round(self.brightness.value()*255/100),self.current.value())

    def _guide(self):
        candidates=[Path(__file__).resolve().parents[3]/'docs/esp32-ws2812-usb.md',
            Path(sysconfig.get_path('data'))/'share/beatlight/docs/esp32-ws2812-usb.md']
        path=next((p for p in candidates if p.is_file()),None)
        if path is None:self.error='Guia não encontrado: docs/esp32-ws2812-usb.md';return
        dialog=QDialog(self);dialog.setWindowTitle('ESP32 USB · ligação, firmware e operação');dialog.resize(980,760)
        layout=QVBoxLayout(dialog);browser=QTextBrowser();browser.setOpenExternalLinks(True)
        browser.document().setBaseUrl(QUrl.fromLocalFile(str(path)));browser.setMarkdown(path.read_text(encoding='utf-8'))
        layout.addWidget(browser)
        close=QDialogButtonBox(QDialogButtonBox.StandardButton.Close);close.rejected.connect(dialog.reject);layout.addWidget(close)
        dialog.exec()

    def _scan(self):
        self.refresh.setEnabled(False)
        def scan():
            try:
                try:ports,error=list_ports(),''
                except Exception as exc:ports,error=[],str(exc)
                if not self.closing:self.portsReady.emit(ports,error)
            except RuntimeError:pass  # Qt may already have destroyed the closed page.
        Thread(target=scan,name='pixel-ports',daemon=True).start()

    def _ports_ready(self,ports,error):
        if self.closing:return
        previous=self.port.currentData() or self.saved_port
        self.port.clear()
        for device,label in ports:self.port.addItem(label,device)
        if not ports:self.port.addItem('Nenhuma porta COM',None)
        index=self.port.findData(previous)
        if index>=0:self.port.setCurrentIndex(index)
        self.refresh.setEnabled(True)
        if error:self.error=error

    def _connect(self):
        if self.preview_only:return
        self.generation+=1;self.pending=False;self.error=''
        if not self.runtime.closed:self.runtime.disconnect();return
        try:
            self.runtime.connect(self.port.currentData(),self._config());self._save()
        except (ValueError,OSError) as exc:self.error=str(exc)

    def _source_changed(self):
        self.generation+=1;self.pending=False
        if self.runtime.status().armed:self.runtime.arm(False)

    def _prepare(self):
        if self.page.bridge.operator.get('simulation'):return
        source=self.source.currentData()
        if not source or not self.page.bridge.ready_state:return
        self._off();self.error=''
        expression='(()=>{try{BeatlightPixel.prepareWs2812('+json.dumps(source)+');return "ok"}catch(e){return e.message}})()'
        self.page.webpage.runJavaScript(expression,lambda value:self._prepared(value))

    def _prepared(self,value):
        if self.closing:return
        self.error='' if value=='ok' else str(value or 'Não foi possível preparar a fita.')
        self.last_sources=-10

    def _arm(self,enabled):
        if enabled and getattr(self,'preview_only',False):
            self._off();self.error='Somente simulação: selecione Saída física · ESP32 USB para transmitir.';return
        if enabled and self.page.bridge.operator.get('simulation'):
            self._off();return
        self.generation+=1;self.pending=False;self.error=''
        try:
            self.runtime.arm(enabled)
            if enabled:self.page.webpage.runJavaScript('BeatlightPixel.arm(true)')
            self._save()
        except ValueError as exc:self.error=str(exc)

    def _off(self):
        self.generation+=1;self.pending=False
        self.runtime.arm(False)

    def _operator_changed(self):
        state=self.page.bridge.operator
        if state.get('simulation'):
            self._off();return
        if state.get('blackout') or not state.get('armed',False):
            # Ignore samples requested before blackout, even if their JS callback
            # arrives after the priority command has already cleared the strip.
            self.generation+=1;self.pending=False;self.runtime.blackout()

    def _bridge_ready(self):
        self._off();self.reading_sources=False;self.source_timeout=False;self.sources_payload=None;self.last_sources=-10
        self.set_preview_only(self.preview_only)

    def _sources(self,payload):
        self.reading_sources=False
        self.source_timeout=False
        if self.closing:return
        if payload==self.sources_payload:return
        try:
            data=json.loads(payload)
            previous=self.source.currentData() or self.desired_id
            if self.runtime.status().armed and not any(item['id']==previous for item in data):
                self._off();self.error='A fita física foi removida do projeto. Escolha outra fita e ative novamente.'
            self.source.blockSignals(True);self.source.clear()
            for item in data:self.source.addItem(f"{item['name']} · {item['pixels']} px",item['id'])
            index=self.source.findData(previous)
            if index>=0:self.source.setCurrentIndex(index)
            self.source.blockSignals(False)
            self.desired_id=self.source.currentData() or ''
            self.sources_payload=payload
        except (ValueError,TypeError,KeyError):self.source.blockSignals(False)

    def _frame(self,payload,generation,source,at):
        if self.closing or generation!=self.generation:return
        self.pending=False
        if not self.runtime.status().armed:return
        try:
            frame=json.loads(payload)
            if isinstance(frame,dict) and 'error' in frame:raise ValueError(frame['error'])
            data=rgb_payload(frame,source)
            if not self.runtime.submit(data,at):raise ValueError('Quadro atrasado; saída física apagada. Ative novamente para retomar.')
        except (ValueError,TypeError) as exc:
            self.error=str(exc);self._off()

    def _tick(self):
        if self.closing:return
        at=monotonic();state=self.runtime.status();ready=self.page.view is not None and self.page.bridge.ready_state
        if ready and not self.preview_only and not self.reading_sources and at-self.last_sources>=1:
            self.reading_sources=True;self.last_sources=at;self.source_request_at=at
            self.page.webpage.runJavaScript('JSON.stringify(BeatlightPixel.outputSources())',self._sources)
        if self.reading_sources and at-self.source_request_at>2 and not self.source_timeout:
            self.source_timeout=True;self.fail('A prévia não respondeu; saída física apagada. Reabra a prévia antes de ativar novamente.')
        if state.armed and ready:
            if self.pending and at-self.request_at>.25:
                self.error='Motor de efeitos não respondeu a tempo; saída física apagada.';self._off()
            elif not self.pending:
                source=self.source.currentData();generation=self.generation
                self.pending=True;self.request_at=at
                expression='JSON.stringify((()=>{try{return BeatlightPixel.outputFrame('+json.dumps(source)+')}catch(e){return {error:e.message}}})())'
                self.page.webpage.runJavaScript(expression,lambda payload,g=generation,s=source,t=at:self._frame(payload,g,s,t))
        elif state.armed:self._off()
        if not getattr(self.page.owner,'visuals_active',True):return
        if at-self.last_status<.2:return
        self.last_status=at;connected=state.state=='connected';busy=state.state in ('connecting','stopping')
        self.port.setEnabled(self.runtime.closed);self.brightness.setEnabled(self.runtime.closed);self.current.setEnabled(self.runtime.closed)
        self.connect_button.setText('Conectando…' if state.state=='connecting' else 'Desconectar' if not self.runtime.closed else 'Conectar ESP32')
        self.connect_button.setEnabled(not self.closing and not self.preview_only and state.state!='stopping')
        virtual=self.page.bridge.operator.get('simulation',False)
        self.source.setEnabled(not self.preview_only and not state.armed and not virtual);self.prepare.setEnabled(not self.preview_only and ready and not state.armed and not virtual and not self.source_timeout and self.source.count()>0)
        self.enable.setEnabled(not self.preview_only and connected and ready and not virtual and not self.source_timeout and self.source.count()>0)
        self.enable.setChecked(state.armed);self.enable.setText('Saída física ATIVA' if state.armed else 'Ativar saída física')
        self.off.setEnabled(connected or busy)
        if self.preview_only:self.status.setText('Projeto atual em simulação · conexão e quadros USB bloqueados. Use áudio/Link ou Demonstração na prévia.')
        elif virtual:self.status.setText('Montagem temporária · saída física desativada.')
        elif self.error or state.error:self.status.setText(self.error or state.error)
        elif connected:
            sending=state.armed and state.last_frame and at-state.last_frame<.3
            self.status.setText(f"{state.port} · ESP32 {state.firmware} · 300 WS2812 · "+('TRANSMITINDO' if sending else 'SAÍDA APAGADA')+f" · {state.frames} quadros confirmados · {state.fps:.1f} fps · {state.dropped} substituídos/atrasados")
        elif busy:self.status.setText('Conectando e verificando firmware…' if state.state=='connecting' else 'Apagando a fita e encerrando USB…')
        else:self.status.setText('Desconectado · fonte externa 5 V · brilho inicial 25% e limite estimado 2.000 mA.')

    def fail(self,message):self.error=message;self._off()

    def shutdown(self):
        if self.closing:return
        self.closing=True;self.generation+=1;self.timer.stop();self.runtime.disconnect()
