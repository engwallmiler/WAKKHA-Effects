"""Mapeamento das quatro saídas WS2812 do ESP32, separado do desenho da prévia."""
import json
import os
import sysconfig
from pathlib import Path
import tempfile
from threading import Thread
from time import monotonic
from PySide6.QtCore import QTimer,Signal,QUrl
from PySide6.QtWidgets import (QWidget,QGroupBox,QGridLayout,QHBoxLayout,QVBoxLayout,
    QComboBox,QPushButton,QLabel,QSpinBox,QDialog,QDialogButtonBox,QTextBrowser,QCheckBox)
from beatlight.pixel.usb import PixelUsbOutput,list_ports
from beatlight.pixel.usb_protocol import OutputConfig,outputs_payload,PINS


class PixelUsbPanel(QWidget):
    portsReady=Signal(object,str)

    def __init__(self,page,runtime=None):
        super().__init__(page)
        self.page=page;self.runtime=runtime or PixelUsbOutput()
        self.path=page.owner.store.path.parent/'pixel-usb.json'
        self.closing=False;self.pending=False;self.generation=0
        self.preview_only=True
        self._inflight=None;self._frame_serial=0;self._last_good_at=0;self._recovering=False
        self._last_tick=0;self._tick_gap=0;self._last_sample=-10;self._health={};self._roundtrip_ms=0
        self._last_gate=None
        self._bind_journal()
        self.request_at=0;self.last_sources=-10;self.last_status=-10;self.reading_sources=False
        self.error='';self.desired_id='';self.preparing=False;self.source_revision=0;self.source_metadata={};saved={}
        try:
            if self.path.exists() and self.path.stat().st_size<4096:
                saved=json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(saved,dict):saved={}
                OutputConfig(saved.get('brightness',64),saved.get('milliamps',2000))
                self.desired_id=saved.get('strip_id','') if isinstance(saved.get('strip_id',''),str) else ''
        except (OSError,ValueError,TypeError):saved={}
        mappings=saved.get('outputs',[])
        if not isinstance(mappings,list) or len(mappings)!=4 or any(not isinstance(row,dict) or row.get('pin')!=pin or type(row.get('enabled')) is not bool or not isinstance(row.get('strip_id'),str) for row,pin in zip(mappings,PINS)):mappings=[]
        self.desired_ids=[row['strip_id'] for row in mappings] if mappings else [self.desired_id,'','','']
        self.active_sources=(None,)*4;self.active_pixels=(0,)*4
        outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0)
        header=QHBoxLayout();self.fold=QPushButton('▸ ESP32 USB · configurar 4 saídas');self.fold.setCheckable(True)
        header.addWidget(self.fold,1);outer.addLayout(header)
        self.mode=QComboBox();self.mode.addItem('Simular projeto atual · sem USB',True);self.mode.addItem('Saída física · ESP32 USB',False)
        self.mode.setToolTip('Simular usa o projeto existente, incluindo barras e grupos, e bloqueia conexão e quadros USB. A fonte pode ser áudio/Link ou demonstração.')
        header.insertWidget(0,self.mode)
        self.mode.currentIndexChanged.connect(lambda:self.set_preview_only(self.mode.currentData()))
        box=QGroupBox('ESP32 USB · 4 saídas WS2812 · até 300 LEDs por saída / 1.200 no total')
        self.controls_box=box;box.setVisible(False)
        self.fold.toggled.connect(lambda opened:(box.setVisible(opened),self.fold.setText(('▾' if opened else '▸')+' ESP32 USB · configurar 4 saídas')))
        grid=QGridLayout(box);grid.setContentsMargins(10,6,10,8);grid.setHorizontalSpacing(8)
        self.port=QComboBox();self.port.setMinimumWidth(150)
        self.refresh=QPushButton('↻ Portas');self.refresh.clicked.connect(self._scan)
        self.connect_button=QPushButton('Conectar ESP32');self.connect_button.clicked.connect(self._connect)
        self.source=QComboBox();self.source.setMinimumWidth(150)
        self.source.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);self.source.setMinimumContentsLength(12)
        self.prepare=QPushButton('Preparar fita WS2812')
        self.prepare.setToolTip('Prepara somente a fita selecionada, com a quantidade indicada abaixo. Preserva nome, desenho e conexões; não transmite nem ativa a saída.')
        self.enable=QPushButton('Ativar saídas físicas');self.enable.setCheckable(True);self.enable.clicked.connect(self._arm)
        self.enable.setStyleSheet('QPushButton:checked {background:#1b684e;border:2px solid #59e1af;color:white;}')
        self.off=QPushButton('APAGAR TODAS');self.off.clicked.connect(lambda:self._off())
        self.off.setStyleSheet('QPushButton {background:#6f2929;color:white;border:1px solid #df7770;font-weight:800;}')
        header.addWidget(self.enable);header.addWidget(self.off)
        self.reload=QPushButton('Reabrir prévia');self.reload.clicked.connect(page.reload_preview);header.addWidget(self.reload)
        grid.addWidget(self.port,0,0,1,2);grid.addWidget(self.refresh,0,2);grid.addWidget(self.connect_button,0,3)
        for column,title in enumerate(('Saída habilitada','Fita lógica do projeto','LEDs físicos','Preparação')):grid.addWidget(QLabel(title),1,column)
        self.pixel_count=QSpinBox();self.pixel_count.setRange(1,300);self.pixel_count.setValue(300)
        self.pixel_count.setToolTip('Quantidade total de LEDs físicos da fita lógica selecionada, somando seus trechos. Um LED = um pixel WS2812.')
        self.sources=[self.source];self.pixel_counts=[self.pixel_count];self.prepares=[self.prepare];self.output_enabled=[]
        for i,pin in enumerate(PINS):
            if i:
                source=QComboBox();source.setMinimumContentsLength(16);source.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
                count=QSpinBox();count.setRange(1,300);count.setValue(300)
                prepare=QPushButton('Preparar fita WS2812')
                self.sources.append(source);self.pixel_counts.append(count);self.prepares.append(prepare)
            enabled=QCheckBox(f'{i+1} · GPIO {pin}');enabled.setChecked(mappings[i]['enabled'] if mappings else i==0);self.output_enabled.append(enabled)
            for column,widget in enumerate((enabled,self.sources[i],self.pixel_counts[i],self.prepares[i])):grid.addWidget(widget,i+2,column)
            enabled.toggled.connect(lambda _,row=i:self._mapping_changed(row))
            self.sources[i].currentIndexChanged.connect(lambda _,row=i:self._source_changed(row))
            self.prepares[i].clicked.connect(lambda _,row=i:self._prepare(row))
            self.sources[i].setToolTip('Escolha uma fita lógica ou cabo contínuo. A mesma fita pode alimentar várias saídas para cópias exatas. Alterar o mapeamento exige reconectar.')
            self.pixel_counts[i].setMaximumWidth(96)
        grid.setColumnStretch(1,1)
        self.source_info=QLabel('Selecione a fita do projeto.');self.source_info.setWordWrap(True)
        grid.addWidget(self.source_info,6,0,1,4)
        limits=QHBoxLayout();limits.setContentsMargins(0,0,0,0)
        limits.addWidget(QLabel('Teto de brilho'))
        self.brightness=QSpinBox();self.brightness.setRange(0,100);self.brightness.setSuffix('%');self.brightness.setValue(round(saved.get('brightness',64)*100/255));limits.addWidget(self.brightness)
        limits.addWidget(QLabel('Limite total estimado'))
        self.current=QSpinBox();self.current.setRange(500,20000);self.current.setSingleStep(500);self.current.setSuffix(' mA');self.current.setValue(saved.get('milliamps',2000));limits.addWidget(self.current)
        limits.addWidget(QLabel('5 V externos · GND comum · conversor 3,3 → 5 V em cada saída'),1)
        self.guide=QPushButton('Instruções');self.guide.clicked.connect(self._guide);limits.addWidget(self.guide)
        grid.addLayout(limits,7,0,1,4)
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
            self._off('simulation_mode','Modo de simulação selecionado; saída física desativada.')
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
            config=OutputConfig(round(self.brightness.value()*255/100),self.current.value())
            data={'version':2,'port':self.port.currentData() or '', 'strip_id':self.source.currentData() or '',
                  'brightness':config.brightness,'milliamps':config.milliamps,
                  'outputs':[{'pin':pin,'enabled':enabled.isChecked(),'strip_id':source.currentData() or ''} for pin,enabled,source in zip(PINS,self.output_enabled,self.sources)]}
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=self.path.parent,suffix='.tmp',delete=False) as stream:
                temporary=Path(stream.name);json.dump(data,stream,ensure_ascii=False);stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,self.path)
        except (OSError,ValueError) as exc:
            self.error=f'Ajustes USB não salvos: {exc}';self._log('WARNING','output.settings_save_failed',self.error)
        finally:
            if temporary and temporary.exists():temporary.unlink()

    def _mapping(self):
        sources=[];counts=[]
        for pin,enabled,source in zip(PINS,self.output_enabled,self.sources):
            identity=source.currentData() if enabled.isChecked() else None
            item=self.source_metadata.get(identity)
            if enabled.isChecked() and (not item or not 1<=item['leds']<=300):raise ValueError(f'GPIO {pin}: selecione e prepare uma fita com 1 a 300 LEDs.')
            sources.append(identity);counts.append(item['leds'] if identity else 0)
        if not any(counts):raise ValueError('Habilite pelo menos uma saída física.')
        return tuple(sources),tuple(counts)

    def _config(self):
        _,counts=self._mapping()
        return OutputConfig(round(self.brightness.value()*255/100),self.current.value(),counts)

    def _guide(self):
        candidates=[Path(__file__).resolve().parents[3]/'docs/esp32-quatro-saidas.md',
            Path(sysconfig.get_path('data'))/'share/beatlight/docs/esp32-quatro-saidas.md']
        path=next((p for p in candidates if p.is_file()),None)
        if path is None:self.error='Guia não encontrado: docs/esp32-quatro-saidas.md';return
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
        if error:self.error=error;self._log('WARNING','usb.port_scan_failed',error)

    def _connect(self):
        if self.preview_only:return
        self.generation+=1;self.pending=False;self.error=''
        if not self.runtime.closed:
            self._off('disconnect','Desconexão solicitada pelo operador.');self.runtime.disconnect();return
        try:
            config=self._config();self.active_sources,self.active_pixels=self._mapping()
            self.runtime.connect(self.port.currentData(),config);self._save()
        except (ValueError,OSError) as exc:
            self.error=str(exc);self._log('ERROR','output.connection_rejected',self.error)

    def _mapping_changed(self,row=0):
        self._source_changed(row)

    def _source_changed(self,row=0):
        self._off('mapping_changed','Mapeamento das saídas alterado; reconexão necessária.')
        self.desired_ids[row]=self.sources[row].currentData() or ''
        self.desired_id=self.desired_ids[0]
        item=self.source_metadata.get(self.desired_ids[row])
        if item:
            self.pixel_counts[row].setValue(item['leds'])
            self.source_info.setText(f"GPIO {PINS[row]} · {item['name']} · {item['leds']} LEDs · {item['pixels']} pixels · {item['profile'].upper()}")
        else:self.source_info.setText('Selecione a fita do projeto.')
        self.error='';self.last_status=-10
        if not self.runtime.closed:
            self.runtime.disconnect();self.error='Mapeamento alterado. Conecte o ESP32 novamente para aplicar as saídas.'
        self._save()

    def _prepare(self,row=0):
        if self.preview_only or self.preparing or self.page.bridge.operator.get('simulation'):return
        source=self.sources[row].currentData()
        if not source or not self.page.bridge.ready_state:return
        self._off('prepare','Preparação de fita solicitada.');self.error='';self.preparing=True;self.preparing_at=monotonic();generation=self.generation
        self.source_revision+=1;self.reading_sources=False;self.last_status=-10
        for widget in (*self.sources,*self.pixel_counts,*self.prepares,*self.output_enabled):widget.setEnabled(False)
        self.enable.setEnabled(False)
        expression='JSON.stringify((()=>{try{BeatlightPixel.prepareWs2812('+json.dumps(source)+','+str(self.pixel_counts[row].value())+');return {sources:BeatlightPixel.outputSources()}}catch(e){return {error:e.message}}})())'
        self.page.webpage.runJavaScript(expression,lambda value:self._prepared(value,generation,source))

    def _prepared(self,value,generation,source):
        if self.closing or generation!=self.generation:return
        self.preparing=False;self.last_sources=-10;self.last_status=-10
        try:
            data=json.loads(value)
            if 'error' in data:raise ValueError(data['error'])
            self._sources(json.dumps(data['sources']))
            item=self.source_metadata[source]
            self.source_info.setText(f"Pronta: {item['name']} · WS2812 · {item['pixels']} LEDs individuais. Clique Ativar saídas físicas após conectar.")
            self._save()
        except (ValueError,TypeError,KeyError) as exc:
            self.error=str(exc) or 'Não foi possível preparar a fita.';self._log('ERROR','output.prepare_failed',self.error)

    def _arm(self,enabled):
        if self.preparing:return
        if enabled and getattr(self,'preview_only',False):
            self._off();self.error='Somente simulação: selecione Saída física · ESP32 USB para transmitir.';return
        if enabled and self.page.bridge.operator.get('simulation'):
            self._off();return
        if enabled and self._inflight is not None:
            self.error='Aguardando resposta pendente da prévia. Se persistir, use Reabrir prévia.';return
        if not enabled:self._off();return
        self.generation+=1;self.pending=False;self.error=''
        try:
            if enabled and self._mapping()!=(self.active_sources,self.active_pixels):raise ValueError('Mapeamento ou quantidade alterados. Desconecte e conecte o ESP32 novamente.')
            self.runtime.arm(enabled)
            if enabled:
                self._last_good_at=monotonic();self._recovering=False;self._last_gate=None
                self._log('INFO','output.activated','Saídas ativadas pelo operador.')
                self.page.webpage.runJavaScript('BeatlightPixel.arm(true)')
            self._save()
        except ValueError as exc:self.error=str(exc);self._log('WARNING','output.activation_rejected',self.error)

    def _off(self,reason='manual_stop',message='Saídas apagadas pelo operador.',level='INFO'):
        was_armed=self.runtime.status().armed
        if reason=='manual_stop':self.error=''
        self.generation+=1;self.pending=False
        self._recovering=False
        if self.preparing:
            self.preparing=False;self.source_revision+=1;self.reading_sources=False;self.last_sources=-10;self.last_status=-10
        self.runtime.arm(False)
        if was_armed or level in ('WARNING','ERROR'):self._log(level,'output.'+reason,message)

    def _bind_journal(self):
        journal=getattr(self.page.owner,'output_journal',None)
        if journal and hasattr(self.runtime,'set_event_sink'):self.runtime.set_event_sink(journal.event)

    def _log(self,level,code,message,**extra):
        journal=getattr(self.page.owner,'output_journal',None)
        if not journal:return
        from dataclasses import asdict
        journal.event(level,code,message,usb=asdict(self.runtime.status()),sources=self.active_sources,
            preview_only=self.preview_only,request_age_ms=max(0,monotonic()-self.request_at)*1000 if self._inflight is not None else 0,
            since_good_ms=max(0,monotonic()-self._last_good_at)*1000 if self._last_good_at else 0,
            gui_gap_ms=self._tick_gap*1000,roundtrip_ms=self._roundtrip_ms,health=self._health,audio=self._audio_health(),**extra)

    def _audio_health(self):
        runtime=getattr(self.page.owner,'runtime',None)
        if runtime is None:return {}
        status=runtime.status()
        return {'state':status.state,'error':status.error,'blocks':status.blocks,
            'dropped_blocks':status.dropped_blocks,'queue_depth':status.queue_depth,'age_ms':status.audio_age*1000}

    def _soft_gap(self):
        if self._recovering:return
        self._recovering=True;self.runtime.blackout()
        self.error='Prévia atrasada: saída temporariamente apagada; aguardando quadro novo.'
        self._log('WARNING','output.frame_gap','Atraso breve da prévia; quadro antigo descartado e saída temporariamente apagada.')

    def _frame_received(self,payload,serial,generation,source,at):
        if serial!=self._inflight:return
        self._inflight=None
        self._frame(payload,generation,source,at)

    def _operator_changed(self):
        state=self.page.bridge.operator
        if state.get('simulation'):
            self._off('temporary_simulation','Montagem temporária selecionada.');return
        if state.get('blackout') or not state.get('armed',False):
            # Ignore samples requested before blackout, even if their JS callback
            # arrives after the priority command has already cleared the strip.
            self.generation+=1;self.pending=False;self.runtime.blackout()

    def _bridge_ready(self):
        self._off('preview_reload','Prévia aberta ou recarregada; reativação física manual necessária.')
        self._frame_serial+=1;self._inflight=None
        self.preparing=False;self.source_revision+=1;self.reading_sources=False;self.source_timeout=False;self.sources_payload=None;self.last_sources=-10
        self.set_preview_only(self.preview_only)

    def _sources(self,payload,revision=None):
        if revision is not None and revision!=self.source_revision:return
        self.reading_sources=False
        self.source_timeout=False
        if self.closing:return
        if payload==self.sources_payload:return
        try:
            data=json.loads(payload)
            if not isinstance(data,list) or any(not isinstance(item,dict) or not isinstance(item.get('id'),str) or not isinstance(item.get('name'),str) or not isinstance(item.get('profile'),str) or type(item.get('leds')) is not int or type(item.get('pixels')) is not int for item in data):return
            ids={item['id'] for item in data}
            if self.runtime.status().armed and any(source and source not in ids for source in self.active_sources):
                self.error='Uma fita física foi removida do projeto. Confira o mapeamento e conecte novamente.'
                self._off('source_removed',self.error,'WARNING')
            for row,source in enumerate(self.sources):
                previous=source.currentData() or self.desired_ids[row]
                source.blockSignals(True);source.clear()
                for item in data:source.addItem(f"{item['name']} · {item['pixels']} px · {item['profile'].upper()}",item['id'])
                index=source.findData(previous)
                if previous and index<0:source.addItem('Fita removida · selecione outra',previous);index=source.count()-1
                if index>=0:source.setCurrentIndex(index)
                source.blockSignals(False);self.desired_ids[row]=source.currentData() or ''
            self.desired_id=self.source.currentData() or ''
            self.source_metadata={item['id']:item for item in data}
            descriptions=[]
            for row,source in enumerate(self.sources):
                item=self.source_metadata.get(source.currentData())
                if item:self.pixel_counts[row].setValue(item['leds'])
                if self.output_enabled[row].isChecked():descriptions.append(f"GPIO {PINS[row]}: {item['name']} · {item['pixels']} px" if item else f'GPIO {PINS[row]}: fita ausente')
            self.source_info.setText(' | '.join(descriptions) or 'Nenhuma saída habilitada.')
            if not self.runtime.closed:
                try:changed=self._mapping()!=(self.active_sources,self.active_pixels)
                except ValueError:changed=True
                if changed:
                    self.error='Quantidade ou fita alterada no projeto. Conecte novamente para aplicar o mapeamento.'
                    self._off('project_mapping_changed',self.error,'WARNING');self.runtime.disconnect()
            self.sources_payload=payload
        except (ValueError,TypeError,KeyError):
            for source in self.sources:source.blockSignals(False)

    def _frame(self,payload,generation,source,at):
        if self.closing or generation!=self.generation:return
        self.pending=False
        if not self.runtime.status().armed:return
        now=monotonic()
        self._roundtrip_ms=(now-at)*1000
        if now-self._last_good_at>=.75:
            self.fail('Prévia sem quadros novos por 750 ms; saída desarmada. Ative novamente após a prévia responder.','frame_timeout');return
        if not 0<=now-at<=.25:
            self._soft_gap();return
        try:
            frame=json.loads(payload)
            if isinstance(frame,dict) and 'error' in frame:raise ValueError(frame['error'])
            if isinstance(frame,dict) and isinstance(frame.get('diagnostics'),dict):self._health=frame['diagnostics']
            state=self.runtime.status()
            data=outputs_payload(frame,source,self.active_pixels,state.protocol)
            if not self.runtime.submit(data,at):
                if self.runtime.status().armed:self._soft_gap()
                return
            self._last_good_at=monotonic()
            if self._recovering:
                self._log('INFO','output.recovered','Quadro novo recebido; envio retomado sem rearmar a saída.')
                self._recovering=False;self.error=''
            gate=self._health.get('gate')
            if gate!=self._last_gate:
                self._last_gate=gate
                if gate:self._log('INFO','output.gate','Estado do motor de efeitos: '+str(gate))
        except (ValueError,TypeError) as exc:
            self.fail(str(exc),'invalid_frame')

    def _tick(self):
        if self.closing:return
        self._bind_journal()
        at=monotonic();self._tick_gap=at-self._last_tick if self._last_tick else 0;self._last_tick=at
        state=self.runtime.status();ready=self.page.view is not None and self.page.bridge.ready_state
        if state.armed and self._tick_gap>.25 and at-self._last_good_at<.75:self._soft_gap()
        if self.preparing and at-self.preparing_at>2:
            self.fail('A preparação não respondeu. Reabra a prévia e prepare a fita novamente.','prepare_timeout')
        if ready and not self.preview_only and not self.preparing and not self.reading_sources and at-self.last_sources>=1:
            self.reading_sources=True;self.last_sources=at;self.source_request_at=at
            revision=self.source_revision
            self.page.webpage.runJavaScript('JSON.stringify(BeatlightPixel.outputSources())',lambda payload,r=revision:self._sources(payload,r))
        if self.reading_sources and at-self.source_request_at>2 and not self.source_timeout:
            self.source_timeout=True;self.fail('A prévia não respondeu; saída física apagada. Reabra a prévia antes de ativar novamente.','source_timeout')
        if state.armed and ready:
            if at-self._last_good_at>=.75:
                self.fail('Prévia sem quadros novos por 750 ms; saída desarmada. Ative novamente após a prévia responder.','frame_timeout')
            elif self._inflight is not None and at-self.request_at>.25:self._soft_gap()
            elif self._inflight is None:
                source=self.active_sources;generation=self.generation
                self.pending=True;self.request_at=at;self._frame_serial+=1;serial=self._frame_serial;self._inflight=serial
                expression='JSON.stringify((()=>{try{const f=BeatlightPixel.outputFrames('+json.dumps(source)+');f.diagnostics=BeatlightPixel.outputHealth();return f}catch(e){return {error:e.message}}})())'
                self.page.webpage.runJavaScript(expression,lambda payload,n=serial,g=generation,s=source,t=at:self._frame_received(payload,n,g,s,t))
        elif state.armed:self.fail('Motor da prévia indisponível; saída desarmada.','preview_unavailable')
        state=self.runtime.status()
        journal=getattr(self.page.owner,'output_journal',None)
        if journal and state.armed and at-self._last_sample>=1:
            from dataclasses import asdict
            self._last_sample=at
            journal.sample(usb=asdict(state),gui_gap_ms=self._tick_gap*1000,request_ms=(at-self.request_at)*1000 if self.pending else 0,roundtrip_ms=self._roundtrip_ms,health=self._health,audio=self._audio_health())
        if not getattr(self.page.owner,'visuals_active',True):return
        if at-self.last_status<.2:return
        self.last_status=at;connected=state.state=='connected';busy=state.state in ('connecting','stopping')
        self.port.setEnabled(self.runtime.closed);self.brightness.setEnabled(self.runtime.closed);self.current.setEnabled(self.runtime.closed)
        self.connect_button.setText('Conectando…' if state.state=='connecting' else 'Desconectar' if not self.runtime.closed else 'Conectar ESP32')
        self.connect_button.setEnabled(not self.closing and not self.preview_only and state.state!='stopping')
        virtual=self.page.bridge.operator.get('simulation',False)
        editable=not self.preview_only and not state.armed and not virtual and not self.preparing
        for row in range(4):
            self.output_enabled[row].setEnabled(editable)
            enabled=editable and self.output_enabled[row].isChecked()
            self.sources[row].setEnabled(enabled);self.pixel_counts[row].setEnabled(enabled)
            self.prepares[row].setEnabled(enabled and ready and not self.source_timeout and self.sources[row].count()>0)
        self.enable.setEnabled(not self.preview_only and connected and ready and not virtual and not self.preparing and not self.source_timeout and (state.armed or self._inflight is None) and self.source.count()>0)
        self.enable.setChecked(state.armed);self.enable.setText('Saídas físicas ATIVAS' if state.armed else 'Ativar saídas físicas')
        self.off.setEnabled(connected or busy)
        if self.preview_only:self.status.setText('Projeto atual em simulação · conexão e quadros USB bloqueados. Use áudio/Link ou Demonstração na prévia.')
        elif virtual:self.status.setText('Montagem temporária · saída física desativada.')
        elif self.preparing:self.status.setText('Preparando a fita selecionada… saída apagada.')
        elif self.error or state.error:self.status.setText(self.error or state.error)
        elif connected:
            sending=state.armed and state.last_frame and at-state.last_frame<.3
            outputs=sum(n>0 for n in self.active_pixels);total=sum(self.active_pixels)
            self.status.setText(f"{state.port} · ESP32 {state.firmware} · {outputs} saída(s) / {total} LEDs · "+('TRANSMITINDO' if sending else 'SAÍDA APAGADA')+f" · {state.frames} quadros confirmados · {state.fps:.1f} fps · {state.dropped} substituídos/atrasados")
        elif busy:self.status.setText('Conectando e verificando firmware…' if state.state=='connecting' else 'Apagando a fita e encerrando USB…')
        else:self.status.setText('Desconectado · fonte externa 5 V · brilho inicial 25% e limite estimado 2.000 mA.')

    def fail(self,message,reason='preview_failure'):self.error=message;self._off(reason,message,'ERROR')

    def shutdown(self):
        if self.closing:return
        self._off('shutdown','Programa encerrando; saída apagada.')
        self.closing=True;self.generation+=1;self.timer.stop();self.runtime.disconnect()
