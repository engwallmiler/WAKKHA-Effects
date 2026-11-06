"""MIDI Learn e retorno LED, com edição explícita e nenhuma chamada de driver na GUI."""
from copy import deepcopy
from threading import Thread
from time import monotonic
from PySide6.QtCore import QTimer,Signal,Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QGroupBox,QComboBox,QPushButton,QLabel,
    QCheckBox,QSpinBox,QTableWidget,QTableWidgetItem,QAbstractItemView,QHeaderView,QScrollArea)
from beatlight.midi.mapping import ACTIONS,MODES,MidiMapper,default_profile,read_profile,save_profile,address,wire
from beatlight.midi.runtime import MidiRuntime


def describe(binding):
    return '—' if not binding else f"{binding['kind'].upper()} · canal {binding['channel']} · {binding['number']}"


class MidiPage(QWidget):
    portsReady=Signal(object,object,str)
    profileSaved=Signal(object,int,str)

    def __init__(self,owner,runtime=None):
        super().__init__(owner);self.owner=owner;self.runtime=runtime or MidiRuntime();self.path=owner.store.path.parent/'midi-controls.json'
        self.closing=False;self.scanning=False;self.dirty=False;self._filling=False;self._dropped=0;self._last_display=0;self._last_peak_input=-10;self._test_until=0;self._test_feedback={}
        self._saving=False;self._edit_revision=0
        error=''
        try:profile=read_profile(self.path)
        except (OSError,ValueError,TypeError) as exc:profile=default_profile();error=f'Perfil MIDI não recuperado: {exc}'
        self.mapper=MidiMapper(profile);self.actions=list(ACTIONS);self._candidate_text=''
        root=QVBoxLayout(self);root.setContentsMargins(0,0,0,0)
        scroll=QScrollArea();scroll.setWidgetResizable(True);root.addWidget(scroll);body=QWidget();scroll.setWidget(body);layout=QVBoxLayout(body)
        intro=QLabel('AUTO SHOW continua como base. MIDI executa comandos pontuais; Learn não dispara efeitos. Entrada e retorno LED usam as portas MIDI da X1.');intro.setWordWrap(True);layout.addWidget(intro)
        ports=QHBoxLayout();self.input=QComboBox();self.output=QComboBox();self.input.setMinimumContentsLength(20);self.output.setMinimumContentsLength(20)
        self.output.addItem('Sem retorno para LEDs',None)
        self.refresh=QPushButton('Atualizar portas');self.refresh.clicked.connect(self._scan)
        self.connect_button=QPushButton('Conectar MIDI');self.connect_button.clicked.connect(self._connect)
        for widget in (QLabel('Entrada'),self.input,QLabel('Saída LED'),self.output,self.refresh,self.connect_button):ports.addWidget(widget)
        layout.addLayout(ports);self.status=QLabel('MIDI desconectado · clique Atualizar portas.');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.notice=QLabel(error or f'Perfil: {self.path} · use Salvar perfil para manter alterações.');self.notice.setWordWrap(True);layout.addWidget(self.notice)
        self.table=QTableWidget(len(self.actions),4);self.table.setHorizontalHeaderLabels(['Função','Entrada aprendida','Retorno LED','Estado'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.table.setMinimumHeight(340);layout.addWidget(self.table)
        row=QHBoxLayout();self.learn=QPushButton('Ativar Learn');self.learn.setCheckable(True);self.learn.toggled.connect(self._learn)
        self.clear=QPushButton('Limpar entrada');self.clear.clicked.connect(self._clear)
        self.execute=QPushButton('Executar função selecionada');self.execute.clicked.connect(self._execute)
        self.save=QPushButton('Salvar perfil');self.save.clicked.connect(self._save)
        for widget in (self.learn,self.clear,self.execute,self.save):row.addWidget(widget)
        layout.addLayout(row)
        self.learned=QLabel('Selecione uma função, ative Learn, movimente o controle e encerre Learn.');self.learned.setWordWrap(True);layout.addWidget(self.learned)
        controls=QHBoxLayout();self.mode=QComboBox()
        for label,key in zip(('Absoluto · 0 a 127','Relativo · +1 / 127','Relativo · centro 64','Relativo · sinal + magnitude'),MODES):self.mode.addItem(label,key)
        controls.addWidget(QLabel('Knob do pico'));controls.addWidget(self.mode);self.mode.currentIndexChanged.connect(self._mode_changed)
        self.test_level=QSpinBox();self.test_level.setRange(0,100);self.test_level.setValue(75);self.test_level.setSuffix('%');controls.addWidget(QLabel('Pico para teste'));controls.addWidget(self.test_level);controls.addStretch();layout.addLayout(controls)
        group=QGroupBox('Retorno LED da função selecionada');grid=QGridLayout(group)
        self.feedback_enabled=QCheckBox('Retorno habilitado');self.feedback_kind=QComboBox();self.feedback_kind.addItems(['note','cc'])
        self.feedback_channel=QSpinBox();self.feedback_channel.setRange(1,16)
        self.feedback_number=QSpinBox();self.feedback_number.setRange(0,127)
        self.feedback_on=QSpinBox();self.feedback_on.setRange(0,127);self.feedback_on.setValue(127)
        self.feedback_off=QSpinBox();self.feedback_off.setRange(0,127)
        for column,(label,widget) in enumerate((('Retorno',self.feedback_enabled),('Tipo',self.feedback_kind),('Canal',self.feedback_channel),('Número',self.feedback_number),('Valor ligado',self.feedback_on),('Valor desligado',self.feedback_off))):
            grid.addWidget(QLabel(label),0,column);grid.addWidget(widget,1,column)
        self.copy_feedback=QPushButton('Usar endereço aprendido para o LED');self.copy_feedback.clicked.connect(self._copy_feedback)
        self.apply_feedback=QPushButton('Aplicar retorno');self.apply_feedback.clicked.connect(self._apply_feedback)
        self.test_feedback=QPushButton('Testar LED · 1 segundo');self.test_feedback.clicked.connect(self._test_led)
        grid.addWidget(self.copy_feedback,2,0,1,3);grid.addWidget(self.apply_feedback,2,3,1,2);grid.addWidget(self.test_feedback,2,5)
        layout.addWidget(group)
        self.detected=QCheckBox('LEDs de Groove / Breakdown / Build-up acompanham também a detecção automática');self.detected.setChecked(profile['detected_feedback']);self.detected.toggled.connect(self._detected_changed);layout.addWidget(self.detected)
        hint=QLabel('X1 MK1: SHIFT + HOTCUE alterna o modo MIDI. No Controller Editor, use botões em Gate e LED On = For MIDI In para retorno controlado pelo programa. O endereço de saída pode ser copiado do Learn ou editado acima.');hint.setWordWrap(True);layout.addWidget(hint)
        layout.addStretch()
        self.portsReady.connect(self._ports_ready);self.table.currentCellChanged.connect(lambda *_:self._select_row())
        self.profileSaved.connect(self._saved)
        self.input.currentIndexChanged.connect(lambda:self._changed());self.output.currentIndexChanged.connect(lambda:self._changed())
        self.owner.pixel_page.bridge.controlsChanged.connect(self._controls_changed)
        self.owner.pixel_page.commandRejected.connect(self.notice.setText)
        self._refresh_table();self.table.selectRow(0);self._select_row()
        self.timer=QTimer(self);self.timer.setInterval(250);self.timer.timeout.connect(self._poll);self.timer.start()

    def _action(self):return self.actions[max(0,self.table.currentRow())]

    def _changed(self):self._edit_revision+=1;self.dirty=True;self.save.setText('Salvar perfil *');self._refresh_table()

    def _refresh_table(self):
        self.table.blockSignals(True)
        for index,action in enumerate(self.actions):
            mapping=self.mapper.profile['mappings'][action]
            for column,text in enumerate((ACTIONS[action],describe(mapping['input']),describe(mapping['output']),'—')):
                self.table.setItem(index,column,QTableWidgetItem(text))
        self.table.blockSignals(False)

    def _select_row(self):
        self._filling=True;mapping=self.mapper.profile['mappings'][self._action()];binding=mapping['output']
        self.mode.setCurrentIndex(self.mode.findData(mapping['input']['mode'] if mapping['input'] else 'absolute'));self.mode.setEnabled(self._action()=='peak_level')
        self.feedback_enabled.setChecked(binding is not None);self.feedback_kind.setCurrentText(binding['kind'] if binding else 'note')
        for widget,key,default in ((self.feedback_channel,'channel',1),(self.feedback_number,'number',0),(self.feedback_on,'on',127),(self.feedback_off,'off',0)):widget.setValue(binding[key] if binding else default)
        self._filling=False

    def _learn(self,enabled):
        # Gestures queued before a Learn boundary belong to the old mode.
        # They must neither become a new assignment nor fire after Learn ends.
        _,self._dropped=self.runtime.drain()
        if enabled:
            self.mapper.start_learn(self._action(),self.mode.currentData());self._candidate_text='';self.learned.setText('Learn ativo · movimente um único controle. Os efeitos não recebem comandos MIDI durante o aprendizado.')
        else:
            try:
                changed=self.mapper.stop_learn()
                if changed:self._changed();self.learned.setText('Entrada aprendida em memória. Clique Salvar perfil para manter esta associação.')
                else:self.learned.setText('Learn encerrado sem alterar a associação.')
            except ValueError as exc:self.notice.setText(str(exc));self.learned.setText('Entrada não aplicada: '+str(exc))
        self.learn.setText('Encerrar Learn' if enabled else 'Ativar Learn');self.table.setEnabled(not enabled);self.save.setEnabled(not enabled and not self._saving);self.clear.setEnabled(not enabled);self.execute.setEnabled(not enabled)
        for widget in (self.mode,self.copy_feedback,self.apply_feedback,self.test_feedback):widget.setEnabled(not enabled)
        if not enabled:self._select_row()

    def _clear(self):
        profile=deepcopy(self.mapper.profile);profile['mappings'][self._action()]['input']=None;self.mapper.configure(profile);self._changed();self._select_row()

    def _mode_changed(self):
        if self._filling or self._action()!='peak_level':return
        profile=deepcopy(self.mapper.profile);binding=profile['mappings']['peak_level']['input']
        if binding:
            binding['mode']=self.mode.currentData()
            try:self.mapper.configure(profile);self._changed()
            except ValueError as exc:self.notice.setText(str(exc));self._select_row()

    def _copy_feedback(self):
        binding=self.mapper.profile['mappings'][self._action()]['input']
        if not binding:self.notice.setText('Aprenda uma entrada primeiro ou informe o endereço do LED manualmente.');return
        self.feedback_enabled.setChecked(True);self.feedback_kind.setCurrentText(binding['kind']);self.feedback_channel.setValue(binding['channel']);self.feedback_number.setValue(binding['number']);self._apply_feedback()

    def _apply_feedback(self):
        profile=deepcopy(self.mapper.profile);binding=None
        if self.feedback_enabled.isChecked():binding={'kind':self.feedback_kind.currentText(),'channel':self.feedback_channel.value(),'number':self.feedback_number.value(),'on':self.feedback_on.value(),'off':self.feedback_off.value()}
        profile['mappings'][self._action()]['output']=binding
        try:self.mapper.configure(profile);self._changed();self.notice.setText('Retorno aplicado em memória. Use Salvar perfil para manter.')
        except ValueError as exc:self.notice.setText(str(exc))

    def _detected_changed(self,enabled):self.mapper.profile['detected_feedback']=bool(enabled);self._changed()

    def _test_led(self):
        binding=self.mapper.profile['mappings'][self._action()]['output']
        if not binding or self.runtime.status().state!='connected':self.notice.setText('Conecte a saída MIDI e aplique um retorno LED primeiro.');return
        self._test_until=monotonic()+1;self._test_feedback={address(binding,True):(wire(binding,binding['on']),wire(binding,binding['off']))}

    def _execute(self):
        action=self._action();value=self.test_level.value()/100 if action=='peak_level' else None
        if not self.owner.pixel_page.queue_controls([(action,value)]):self.notice.setText('Aguarde a prévia ou reabra o Pixel Studio para executar a função.')

    def _save(self):
        if self.mapper.learning or self._saving:return
        profile=deepcopy(self.mapper.profile)
        info=self.input.currentData();out=self.output.currentData()
        if info:profile['input_port']=info.name
        profile['output_port']=out.name if out else ''
        self._saving=True;revision=self._edit_revision;self.save.setEnabled(False);self.notice.setText('Salvando perfil MIDI…')
        def write():
            error=''
            try:save_profile(self.path,profile)
            except (OSError,ValueError) as exc:error=str(exc)
            try:self.profileSaved.emit(profile,revision,error)
            except RuntimeError:pass
        Thread(target=write,name='midi-profile-writer',daemon=True).start()

    def _saved(self,profile,revision,error):
        self._saving=False;self.save.setEnabled(self.mapper.learning is None)
        if error:self.notice.setText(f'Perfil não salvo: {error}');return
        if revision==self._edit_revision:
            self.mapper.profile=profile;self.dirty=False;self.save.setText('Salvar perfil');self.notice.setText(f'Perfil MIDI salvo: {self.path}')
        else:self.notice.setText('Perfil solicitado salvo. Há novas alterações em memória; use Salvar perfil novamente para mantê-las.')

    def _scan(self):
        if self.scanning:return
        self.scanning=True;self.refresh.setEnabled(False)
        def scan():
            try:inputs,outputs=self.runtime.backend_factory().scan();error=''
            except Exception as exc:inputs,outputs,error=(),(),str(exc)
            try:
                if not self.closing:self.portsReady.emit(inputs,outputs,error)
            except RuntimeError:pass
        Thread(target=scan,name='midi-ports',daemon=True).start()

    def _ports_ready(self,inputs,outputs,error):
        if self.closing:return
        self.scanning=False;self.refresh.setEnabled(True)
        for combo,ports,key in ((self.input,inputs,'input_port'),(self.output,outputs,'output_port')):
            previous=combo.currentData();name=previous.name if previous else self.mapper.profile[key];combo.blockSignals(True);combo.clear()
            if combo is self.output:combo.addItem('Sem retorno para LEDs',None)
            for info in ports:combo.addItem(f'{info.id} · {info.name}',info)
            found=next((i for i in range(combo.count()) if combo.itemData(i) and combo.itemData(i).name==name),-1)
            if found>=0:combo.setCurrentIndex(found)
            combo.blockSignals(False)
        if error:self.notice.setText(error)

    def _connect(self):
        if not self.runtime.closed:
            if self.learn.isChecked():self.learn.setChecked(False)
            self.runtime.stop();return
        info=self.input.currentData();out=self.output.currentData()
        if not info:self.notice.setText('Atualize as portas e escolha a entrada MIDI da X1.');return
        try:self.runtime.connect(info.id,out.id if out else None);self._dropped=0;self.mapper.pressed.clear();self.timer.setInterval(20)
        except ValueError as exc:self.notice.setText(str(exc))

    def _controls_changed(self):
        value=self.owner.pixel_page.bridge.controls.get('peak_level')
        if value is not None and monotonic()-self._last_peak_input>.25:self.mapper.peak=value

    def _poll(self):
        if self.closing:return
        state=self.runtime.status();events,dropped=self.runtime.drain();commands=[]
        if dropped!=self._dropped:
            events=[];self._dropped=dropped;self.mapper.pressed.clear();self.notice.setText('Excesso de mensagens MIDI: lote descartado e botões rearmados. Confira a porta e loops MIDI.')
        for word in events:
            result=self.mapper.accept(word)
            if result:
                if result[0]=='peak_level':self._last_peak_input=monotonic();commands=[item for item in commands if item[0]!='peak_level']
                commands.append(result)
        if commands:self.owner.pixel_page.queue_controls(commands[:64])
        if self.mapper.learning and self.mapper.candidate:
            text=describe(self.mapper.candidate)
            if text!=self._candidate_text:self._candidate_text=text;self.learned.setText(f'Capturado: {text}. Encerre Learn para aplicar; depois salve o perfil.')
        if state.state=='connected' and not self.mapper.learning:
            feedback={} if self.owner.pixel_page.control_blocked else self.mapper.feedback(self.owner.pixel_page.bridge.controls)
            if monotonic()<self._test_until:
                for key,values in self._test_feedback.items():
                    if key in feedback:feedback[key]=values
            self.runtime.set_feedback(feedback)
        active=not self.runtime.closed;interval=20 if active else 250
        if self.timer.interval()!=interval:self.timer.setInterval(interval)
        self.input.setEnabled(not active);self.output.setEnabled(not active)
        self.learn.setEnabled(state.state=='connected' or self.learn.isChecked());self.connect_button.setText('Desconectar MIDI' if active else 'Conectar MIDI')
        if self.owner.visuals_active and self.owner.pages.currentIndex()==10 and monotonic()-self._last_display>=.25:
            translated={'disconnected':'desconectado','connecting':'conectando','connected':'conectado','error':'falha'}[state.state]
            self._last_display=monotonic();self.status.setText(f'MIDI: {translated} · recebidas {state.received} · retorno {state.sent} · descartadas {state.dropped}'+(' · '+state.error if state.error else ''))
            controls=self.owner.pixel_page.bridge.controls
            for index,action in enumerate(self.actions):
                on=controls.get('manual_structure')==action if action in ('groove','breakdown','buildup') else controls.get('drop',False) if action=='drop' else controls.get('continuous',False) if action=='continuous' else controls.get('mode')==action if action in ('auto','organic') else controls.get('queued',False) if action=='next_combo' else controls.get('sync',False) if action=='sync_1_8' else controls.get('cue_sync',False) if action=='cue_sync' else None
                text=f"{round(controls.get('peak_level',0)*100)}%" if action=='peak_level' else 'ATIVO' if on else '—'
                if self.table.item(index,3).text()!=text:self.table.item(index,3).setText(text)

    @property
    def closed_ready(self):return self.runtime.closed and not self._saving

    def shutdown(self):self.closing=True;self.timer.stop();self.runtime.stop()
