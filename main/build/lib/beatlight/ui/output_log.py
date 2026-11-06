"""Nonmodal, bounded output diagnostics; redraws only while visible."""
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
from threading import Thread
from beatlight.diagnostics.pc_time import local_time
from PySide6.QtCore import Qt, QTimer, Signal, QUrl
from PySide6.QtGui import QDesktopServices,QColor
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QLineEdit,
    QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QPlainTextEdit,QFileDialog)


def display_time(value):
    try:return local_time(datetime.fromisoformat(value).timestamp()).strftime('%d/%m/%Y %H:%M:%S.%f')[:-3]
    except (ValueError,TypeError):return str(value)


class OutputLogDialog(QDialog):
    exported=Signal(str,str)
    def __init__(self, journal, parent=None):
        super().__init__(parent);self.journal=journal;self.seen=-1;self.rows=[]
        self.setWindowTitle('Logs da saída · Pixel Studio');self.resize(1100,710)
        self.setMinimumSize(800,520)
        self.setStyleSheet('QTableWidget {background:#11171b;gridline-color:#2e3942;} '
            'QHeaderView::section {background:#20282e;color:#dce5e9;padding:6px;border:1px solid #2e3942;} '
            'QTableWidget::item:selected {background:#29483c;} '
            'QLineEdit,QPlainTextEdit {background:#11171b;border:1px solid #37434c;padding:6px;color:#dce5e9;}')
        layout=QVBoxLayout(self)
        self.summary=QLabel();self.summary.setWordWrap(True);layout.addWidget(self.summary)
        tools=QHBoxLayout();self.level=QComboBox();self.level.addItems(['Todos os eventos','Avisos e erros','Somente erros'])
        self.search=QLineEdit();self.search.setPlaceholderText('Filtrar motivo, código, porta…')
        tools.addWidget(self.level);tools.addWidget(self.search,1)
        self.pause=QPushButton('Pausar lista');self.pause.setCheckable(True);tools.addWidget(self.pause)
        self.export_button=QPushButton('Exportar diagnóstico');tools.addWidget(self.export_button)
        folder=QPushButton('Abrir pasta de logs');tools.addWidget(folder);layout.addLayout(tools)
        self.table=QTableWidget(0,4);self.table.setHorizontalHeaderLabels(['Horário local do PC','Nível','Evento','Motivo'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.setWordWrap(False)
        self.table.verticalHeader().hide();self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0,180);self.table.setColumnWidth(1,85);self.table.setColumnWidth(2,220)
        layout.addWidget(self.table,3)
        self.detail=QPlainTextEdit();self.detail.setReadOnly(True);self.detail.setMaximumBlockCount(250);layout.addWidget(self.detail,1)
        self.notice=QLabel('O registro continua com esta janela fechada. Não contém áudio bruto nem quadros RGB.');layout.addWidget(self.notice)
        close=QPushButton('Fechar');close.clicked.connect(self.close);layout.addWidget(close)
        self.level.currentIndexChanged.connect(self._invalidate);self.search.textChanged.connect(self._invalidate)
        self.pause.toggled.connect(lambda paused:self.pause.setText('Retomar lista' if paused else 'Pausar lista'))
        self.table.itemSelectionChanged.connect(self._detail)
        folder.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(journal.directory))))
        self.export_button.clicked.connect(self._choose_export);self.exported.connect(self._exported)
        self.timer=QTimer(self);self.timer.setInterval(500);self.timer.timeout.connect(self.refresh)

    def showEvent(self,event):
        super().showEvent(event);self.timer.start();self.refresh()

    def hideEvent(self,event):
        self.timer.stop();super().hideEvent(event)

    def _invalidate(self,*args):self.seen=-1;self.refresh()

    def refresh(self):
        if self.pause.isChecked() or self.seen==self.journal.revision:return
        self.seen=self.journal.revision;data=self.journal.snapshot();incident=data['last_incident']
        summary=('Último aviso: '+display_time(incident['time'])+' · '+incident['message']) if incident else 'Nenhum aviso de saída registrado.'
        if data['disk_error']:summary+=' | Disco: '+data['disk_error']
        if data['writes_lost']:summary+=f" | Escritas descartadas por saturação: {data['writes_lost']}"
        self.summary.setText(summary)
        query=self.search.text().casefold();level=self.level.currentIndex()
        selected=self.table.currentRow();identity=self.rows[selected] if 0<=selected<len(self.rows) else None
        self.rows=[r for r in reversed(data['events']) if (level==0 or r['level'] in (('WARNING','ERROR') if level==1 else ('ERROR',))) and (not query or query in json.dumps(r,ensure_ascii=False).casefold())]
        self.table.setUpdatesEnabled(False);self.table.setRowCount(len(self.rows))
        for i,row in enumerate(self.rows):
            for j,value in enumerate((display_time(row['time']),row['level'],row['code'],row['message'])):
                item=QTableWidgetItem(value);item.setToolTip(value)
                if j==1:item.setForeground(QColor({'ERROR':'#ff9c8c','WARNING':'#efca7e'}.get(row['level'],'#8ddbc2')))
                self.table.setItem(i,j,item)
        if identity in self.rows:self.table.selectRow(self.rows.index(identity))
        self.table.setUpdatesEnabled(True)

    def _detail(self):
        row=self.table.currentRow()
        self.detail.setPlainText(json.dumps(self.rows[row],ensure_ascii=False,indent=2) if 0<=row<len(self.rows) else '')

    def _choose_export(self):
        path,_=QFileDialog.getSaveFileName(self,'Exportar diagnóstico da saída','pixel-output-diagnostico.json','JSON (*.json)',options=QFileDialog.Option.DontUseNativeDialog)
        if path:self.export_to(Path(path))

    def export_to(self,path):
        if not self.export_button.isEnabled():return
        data=self.journal.snapshot();self.export_button.setEnabled(False)
        def write():
            temporary=None;error=''
            try:
                with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,suffix='.tmp',delete=False) as stream:
                    temporary=Path(stream.name);json.dump(data,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
                os.replace(temporary,path)
            except OSError as exc:error=str(exc)
            finally:
                if temporary and temporary.exists():temporary.unlink(missing_ok=True)
            try:self.exported.emit(str(path),error)
            except RuntimeError:pass
        Thread(target=write,name='pixel-log-export',daemon=True).start()

    def _exported(self,path,error):
        self.export_button.setEnabled(True);self.notice.setText('Falha ao exportar: '+error if error else 'Diagnóstico exportado: '+path)
