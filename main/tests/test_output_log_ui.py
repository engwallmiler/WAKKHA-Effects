from datetime import datetime,timezone
import json
from PySide6.QtCore import QTimer,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileDialog
from beatlight.ui.output_log import display_time
from beatlight.diagnostics.pc_time import local_time
from test_midi_ui import window,pump


def test_viewer_filters_local_timestamps_exports_and_stops_drawing_when_closed(window,tmp_path):
    app,owner=window;journal=owner.output_journal
    journal.event('ERROR','output.frame_timeout','Prévia sem resposta.',port='COM5')
    owner.pixel_page.logs_button.click();dialog=owner.pixel_page._log_dialog
    assert dialog.isVisible() and dialog.timer.isActive() and not dialog.isModal()
    dialog.search.setText('frame_timeout');dialog.refresh()
    assert dialog.table.rowCount()==1 and 'Prévia sem resposta' in dialog.summary.text()
    dialog.table.selectRow(0);assert 'COM5' in dialog.detail.toPlainText()
    path=tmp_path/'diagnostico.json';dialog.export_to(path)
    pump(app,lambda:path.exists() and dialog.export_button.isEnabled())
    exported=json.loads(path.read_text(encoding='utf-8'))
    assert exported['last_incident']['code']=='output.frame_timeout'
    assert exported['limits']['disk_files']==4
    dialog.close();assert not dialog.timer.isActive()
    owner.pixel_page.logs_button.click();assert owner.pixel_page._log_dialog is dialog
    assert display_time('2026-11-06T03:04:05.123+00:00')==local_time(datetime(2026,11,6,3,4,5,123000,tzinfo=timezone.utc).timestamp()).strftime('%d/%m/%Y %H:%M:%S.%f')[:-3]


def test_file_dialogs_keep_qt_timers_running_and_escape_in_logs_keeps_stage_fullscreen(window):
    app,owner=window;owner.pages.setCurrentIndex(9);owner.pixel_page.toggle_fullscreen()
    owner.pixel_page.show_output_logs();app.processEvents();dialog=owner.pixel_page._log_dialog
    QTest.keyClick(dialog.search,Qt.Key.Key_Escape);app.processEvents()
    assert not dialog.isVisible() and owner.isFullScreen()
    owner.pixel_page.exit_fullscreen()
    assert app.testAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs)
    chooser=QFileDialog(owner);chooser.setOption(QFileDialog.Option.DontUseNativeDialog)
    ticks=[];timer=QTimer();timer.setInterval(10)
    def tick():
        ticks.append(1)
        if len(ticks)>=5:chooser.reject()
    timer.timeout.connect(tick);timer.start()
    QTimer.singleShot(1500,chooser.reject);chooser.exec();timer.stop()
    assert len(ticks)>=5
