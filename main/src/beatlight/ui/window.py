"""Interface e comandos do operador. Trabalhos de driver nunca rodam na GUI."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from time import monotonic
from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget
from beatlight.audio.synthetic import SyntheticSource
from beatlight.audio.wasapi import WasapiSource
from beatlight.configuration.store import Settings, SettingsStore
from beatlight.core.runtime import CaptureRuntime
from beatlight.core.lighting_runtime import LightingRuntime
from beatlight.lighting.config import LightingControls
from beatlight.ui.lighting import (build_lighting_page, update_lighting_view,
    apply_lighting_controls, lighting_form_values, load_lighting_settings)
from beatlight.dsp.pipeline import AudioAnalyzer
from beatlight.ui.rhythm import build_rhythm_page, update_rhythm_view
from beatlight.ui.beat_settings import load_beat_settings, beat_form_values
from beatlight.ui.kicks import build_kick_page, update_kick_view
from beatlight.ui.kick_settings import load_kick_settings, kick_form_values
from beatlight.ui.spectral import build_spectral_page, update_spectral_view
from beatlight.ui.dsp_settings import load_dsp_settings, dsp_form_values
from beatlight.sync.link import LinkRuntime
from beatlight.sync.timeline import apply_link, link_grid
from beatlight.music.grid import grid_clock
from beatlight.ui.link import build_link_page, update_link_view
from beatlight.ui.components import label
from beatlight.ui.stage import build_stage_page, update_stage_view
from beatlight.ui.panels import build_sidebar, build_monitor_page, build_diagnostics_page, build_settings_page
from beatlight.ui.pixel import PixelStudioPage


class JobBridge(QObject):
    completed = Signal(str, object, object)


class MainWindow(QMainWindow):
    def __init__(self, store: SettingsStore, settings: Settings, startup_warning: str = ""):
        super().__init__()
        self.store, self.settings = store, settings
        self.link_runtime = LinkRuntime()
        self._sync_options = (settings.sync_source, settings.link_offset_ms)
        self.runtime = self._make_runtime(settings)
        self.light_runtime = LightingRuntime(lambda: (self._effective_snapshot(), self.runtime.status()),
                                             LightingControls(config=settings.light_config()))
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="device-control")
        self.bridge = JobBridge()
        self.bridge.completed.connect(self._job_done)
        self.busy = False
        self.closing = False
        self.closed_ready = False
        self.devices = []
        self.last_error = ""
        self.last_source_notice = ""
        self._last_state = ""
        self._last_sequence = -1
        self._last_drop_count = 0
        self._render_count = 0
        self._fps_start = monotonic()
        self.setWindowTitle("BEATLIGHT · Pixel Studio & Music")
        self.resize(1440, 960)
        self.setMinimumSize(1100, 760)
        container = QWidget()
        root = QHBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(build_sidebar(self))
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(30, 24, 30, 16)
        layout.setSpacing(18)
        header = QHBoxLayout()
        self.page_title = label("Audio Monitor", "title")
        header.addWidget(self.page_title)
        header.addStretch()
        header.addWidget(label("PIXEL & MUSIC · v0.24", "badge"))
        layout.addLayout(header)
        layout.addWidget(label("Da batida ao palco: acompanhe o groove, a tensão e o drop.", "subtitle"))
        self.pages = QStackedWidget()
        self.pages.addWidget(build_monitor_page(self))
        self.pages.addWidget(build_diagnostics_page(self))
        self.pages.addWidget(build_settings_page(self))
        self.pages.addWidget(build_spectral_page(self))
        self.pages.addWidget(build_kick_page(self))
        self.pages.addWidget(build_rhythm_page(self))
        self.pages.addWidget(build_lighting_page(self))
        self.pages.addWidget(build_stage_page(self))
        self.pages.addWidget(build_link_page(self))
        self.pixel_page=PixelStudioPage(self)
        self.pages.addWidget(self.pixel_page)
        layout.addWidget(self.pages, 1)
        footer = QHBoxLayout()
        self.footer_status = label("●  Pronto para monitorar", "muted")
        footer.addWidget(self.footer_status)
        footer.addStretch()
        footer.addWidget(label("PIXEL STUDIO  /  WS2812 USB  /  v0.24.0", "eyebrow"))
        layout.addLayout(footer)
        root.addWidget(body, 1)
        self.setCentralWidget(container)
        self.light_runtime.start()
        self.timer = QTimer(self)
        self.timer.setInterval(round(1000 / settings.ui_fps))
        self.timer.timeout.connect(self._tick)
        self.timer.start()
        self._event("Motor abstrato de iluminação disponível; ative em Lighting Studio.")
        self._event("Aplicação inicializada. Nenhuma saída física está ativa.")
        if startup_warning:
            self._notice(startup_warning, True)
        QTimer.singleShot(0, self._scan)


    def _make_runtime(self, settings):
        config = settings.dsp_config()
        kick_config = settings.kick_config()
        beat_config = settings.beat_config()
        return CaptureRuntime(settings.queue_capacity, settings.silence_db,
                              analyzer_factory=lambda: AudioAnalyzer(settings.silence_db, config, kick_config, beat_config, self._external_beat))

    def _external_beat(self, at):
        source, offset = self._sync_options
        return grid_clock(link_grid(self.link_runtime.snapshot(), at, offset), at) if source == "link" else None

    def _effective_snapshot(self):
        snapshot = self.runtime.snapshot()
        source, offset = self._sync_options
        return apply_link(snapshot, self.link_runtime.snapshot(), monotonic(), offset) if source == "link" else snapshot

    def _toggle_link(self, checked):
        self._submit("link_start" if checked else "link_stop",
                     self.link_runtime.start if checked else self.link_runtime.stop)

    def _link_options_changed(self, *args):
        self._sync_options = ("link" if self.link_use.isChecked() else "audio", self.link_offset.value())

    def _navigate(self, index):
        self.pages.setCurrentIndex(index)
        if self.nav_group.button(index):
            self.nav_group.button(index).setChecked(True)
        self.page_title.setText(("Audio Monitor", "Diagnósticos", "Configurações", "Análise espectral", "Kick Monitor", "Rhythm Monitor", "Lighting Studio", "Stage Preview", "Ableton Link", "Pixel Studio")[index])
        if index==9:self.pixel_page.ensure_loaded()
        self._tick()




    def _source(self):
        source = self.source_combo.currentData()
        return SyntheticSource(structure_demo=source == "structure_demo", texture_demo=source == "texture_demo") if source in ("synthetic", "structure_demo", "texture_demo") else WasapiSource()

    def _submit(self, name, function):
        if self.busy:
            return
        self.busy = True
        self._tick()
        future = self.executor.submit(function)
        def finished(result):
            try:
                value = result.result()
                self.bridge.completed.emit(name, value, None)
            except Exception as exc:
                self.bridge.completed.emit(name, None, str(exc))
        future.add_done_callback(finished)

    def _scan(self, *args):
        if self.busy:
            return
        source = self._source()
        self._submit("scan", source.devices)

    def _device_details(self, *args):
        index = self.device_combo.currentIndex()
        if 0 <= index < len(self.devices):
            device = self.devices[index]
            self.device_info.setText(f"Nominal: {device.sample_rate:,} Hz · {device.channels} canais".replace(",", "."))
        else:
            self.device_info.setText("Nenhuma saída disponível")

    def _start(self):
        index = self.device_combo.currentIndex()
        if index < 0 or index >= len(self.devices):
            return
        self.last_error = ""
        self._notice("TESTE SINTÉTICO: este sinal é gerado localmente e não captura áudio do Windows." if self.source_combo.currentData() in ("synthetic", "structure_demo", "texture_demo") else "Loopback captura a mixagem da saída, incluindo outros aplicativos. Use WASAPI compartilhado; ASIO nativo não é capturado.")
        self._last_sequence = -1
        self._last_drop_count = 0
        source, device, size = self._source(), self.devices[index], self.block_combo.currentData()
        self._event(f"Abrindo {device.name} • bloco {size} frames.")
        self._submit("start", lambda: self.runtime.start(source, device, size))

    def _stop_capture(self):
        self._submit("stop", self.runtime.stop)

    def _job_done(self, name, value, error):
        self.busy = False
        if error:
            if name == "scan":
                self.devices = []
                self.device_combo.clear()
            self.last_error = error
            self._notice(error, True)
        elif name == "scan":
            prior = self.device_combo.currentData() or self.settings.device_id
            self.devices = value
            self.device_combo.clear()
            for device in value:
                self.device_combo.addItem(device.name + ("  · padrão" if device.is_default else ""), device.id)
            index = next((i for i, d in enumerate(value) if d.id == prior),
                         next((i for i, d in enumerate(value) if d.is_default), 0))
            if value:
                self.device_combo.setCurrentIndex(index)
                self._device_details()
                self._event(f"{len(value)} fonte(s) disponível(is).")
            else:
                self._notice("Nenhum dispositivo Loopback encontrado. Verifique a saída do Windows ou selecione o teste sintético.", True)
        self._tick()
        if self.closing:
            if name == "shutdown" and not error:
                self._finish_shutdown()
            elif name == "shutdown":
                self.closing = False
            else:
                self._submit("shutdown", self._shutdown_runtimes)

    def _tick(self):
        status = self.runtime.status()
        snapshot = self._effective_snapshot()
        running = status.state in ("starting", "running", "stopping")
        mutable = not self.busy and not running and not self.closing
        for widget in (self.source_combo, self.device_combo, self.block_combo,
                       self.refresh_button, self.apply_button, self.import_button,
                       self.queue_spin, self.silence_spin, self.fps_spin, *self.dsp_widgets, *self.kick_widgets, *self.beat_widgets):
            widget.setEnabled(mutable)
        self.start_button.setEnabled(mutable and bool(self.devices))
        self.stop_button.setEnabled(not self.busy and running and not self.closing)
        self.spectral_start.setEnabled(self.start_button.isEnabled())
        self.spectral_stop.setEnabled(self.stop_button.isEnabled())
        state_text = {"stopped": "PARADA", "starting": "ABRINDO", "running": "CAPTURANDO",
                      "stopping": "ENCERRANDO", "error": "ERRO"}.get(status.state, status.state)
        fresh = status.state == "running" and snapshot is not None and status.audio_age < 0.5
        page = self.pages.currentIndex()
        if page==9 or self.pixel_page.bridge.ready_state:
            self.pixel_page.update_music(snapshot,status,monotonic())
        if page == 3:
            update_spectral_view(self, snapshot, status, fresh)
        if page == 4:
            update_kick_view(self, snapshot, status, fresh)
        if page == 5:
            update_rhythm_view(self, snapshot, status)
        # Controles compartilhados continuam atualizados em qualquer página.
        update_lighting_view(self)
        if page == 8:
            update_link_view(self)
        if page == 7:
            update_stage_view(self, snapshot, status, monotonic())
        signal = "CLIPPING" if fresh and snapshot.clipping else "SILÊNCIO" if fresh and snapshot.silent else "SINAL ATIVO" if fresh else state_text
        self.signal_badge.setText(signal)
        self.footer_status.setText("●  " + ("Aguardando novos blocos" if status.state == "running" and not fresh else status.message))
        self.wave.active = self.meter.active = fresh
        self.wave.snapshot = self.meter.snapshot = snapshot
        self.wave.update()
        self.meter.update()
        if status.state != self._last_state:
            self._event(f"Estado: {state_text.lower()} • {status.message}")
            self._last_state = status.state
        if status.notice and status.notice != self.last_source_notice:
            self.last_source_notice = status.notice
            self._notice(status.notice, True)
        if status.error and status.error != self.last_error:
            self.last_error = status.error
            self._notice(status.error, True)
        if status.dropped_blocks > self._last_drop_count:
            self._event(f"Sobrecarga: {status.dropped_blocks} bloco(s) descartado(s).")
            self._last_drop_count = status.dropped_blocks
        fmt = status.stream_format
        if fmt:
            self.metrics["rate"].setText(f"{fmt.sample_rate / 1000:g} kHz")
            self.metrics["channels"].setText(f"{fmt.channels:02d}")
            self.metrics["block"].setText(f"{fmt.block_size / fmt.sample_rate * 1000:.1f} ms")
        self.metrics["age"].setText(f"{max(0, monotonic() - snapshot.acquired_at) * 1000:.0f} ms" if fresh else "—")
        if fresh:
            rms = " / ".join(f"{v:.1f}" for v in snapshot.rms_db[:2])
            peak = " / ".join(f"{v:.1f}" for v in snapshot.peak_db[:2])
            self.level_text.setText(f"RMS  {rms} dBFS\nPICO  {peak} dBFS")
        else:
            self.level_text.setText("RMS —   /   PICO —")
        dsp = f"{snapshot.processing_ms:.2f} ms" if snapshot else "—"
        self.monitor_metrics.setText(f"BLOCOS  {status.blocks:,}     ·     FILA  {status.queue_depth}/{self.settings.queue_capacity}     ·     DESCARTES  {status.dropped_blocks}     ·     DSP  {dsp}")
        self._render_count += 1
        duration = monotonic() - self._fps_start
        if duration >= 1:
            fps = self._render_count / duration
            self._render_count = 0
            self._fps_start = monotonic()
            self.diagnostic_values.setText(
                f"Estado: {state_text}    •    Sessão: {status.elapsed:.1f} s    •    UI: {fps:.1f} atualizações/s\n"
                f"Blocos: {status.blocks}    •    Descartes: {status.dropped_blocks}    •    Fila: {status.queue_depth}/{self.settings.queue_capacity}\n"
                f"DSP: {dsp}    •    Distribuição: {snapshot.delivery_ms:.2f} ms    •    Falhas de continuidade: {snapshot.continuity_errors}\n"
                f"Latência informada pelo driver: {fmt.input_latency * 1000:.1f} ms    •    Último bloco recebido há {status.audio_age:.2f} s"
                if snapshot and fmt else f"Estado: {state_text}    •    UI: {fps:.1f} atualizações/s\nInicie a captura para medir o processamento.")

        if snapshot and snapshot.spectral:
            spectrum = snapshot.spectral
            self.diagnostic_values.setText(self.diagnostic_values.text().split("\nFFT:")[0] +
                f"\nFFT: {spectrum.fft_size} amostras / passo {spectrum.hop_size} / quadro {spectrum.frame_id} / transientes {spectrum.transient_count}")

        diagnostic = self.diagnostic_values.text().split("\nKicks:")[0]
        if snapshot and snapshot.kicks:
            k = snapshot.kicks
            diagnostic += f"\nKicks: {k.count} / quadro {k.frame_id} / atividade {k.score:.3f} / limiar {k.threshold:.3f}"
        elif snapshot and snapshot.kick_error:
            diagnostic += "\nKicks: indisponível — " + snapshot.kick_error
        self.diagnostic_values.setText(diagnostic)

        diagnostic = self.diagnostic_values.text().split("\nBeat Tracker:")[0]
        if snapshot and snapshot.beat:
            b = snapshot.beat
            diagnostic += f"\nBeat Tracker: {b.state} / {b.bpm:.2f} BPM / confiança {b.confidence:.0%} / erro {b.phase_error_ms:+.1f} ms"
        elif snapshot and snapshot.beat_error:
            diagnostic += "\nBeat Tracker: indisponível — " + snapshot.beat_error
        self.diagnostic_values.setText(diagnostic)

        diagnostic = self.diagnostic_values.text().split("\nEstrutura:")[0]
        if snapshot and snapshot.structure:
            m = snapshot.structure
            diagnostic += f"\nEstrutura: {m.state} / tensão {m.tension:.0%} / confiança {m.confidence:.0%} / frase {m.phrase_kick}/8 / pós-drop {m.drop_kicks}/8"
        elif snapshot and snapshot.structure_error:
            diagnostic += "\nEstrutura: indisponível — " + snapshot.structure_error
        self.diagnostic_values.setText(diagnostic)
        light = self.light_runtime.snapshot()
        diagnostic = self.diagnostic_values.text().split("\nIluminação:")[0]
        self.diagnostic_values.setText(diagnostic +
            f"\nIluminação: {light.status} / {light.update_hz:.1f} Hz / {light.processing_ms:.3f} ms / quadro {light.frame_id} / 6 luminárias abstratas")

    def _event(self, text):
        self.events.append(datetime.now(timezone.utc).strftime("%H:%M:%S UTC") + "  " + text.replace("<", "&lt;"))

    def _notice(self, text, error=False):
        self.notice.setText(("Atenção: " if error else "") + text)
        if self.pages.currentIndex() == 2:
            self.settings_notice.setText(("Atenção: " if error else "") + text)
        self._event(text)

    def _current_settings(self):
        return replace(self.settings, sync_source=self._sync_options[0], link_offset_ms=self._sync_options[1], source=self.source_combo.currentData(),
                       device_id=self.device_combo.currentData() or "",
                       block_size=self.block_combo.currentData(),
                       queue_capacity=self.queue_spin.value(), silence_db=self.silence_spin.value(),
                       ui_fps=self.fps_spin.value(), **dsp_form_values(self), **kick_form_values(self), **beat_form_values(self), **lighting_form_values(self))

    def _apply_settings(self):
        try:
            settings = self._current_settings()
            self.store.save(settings)
            self.settings = settings
            self.runtime = self._make_runtime(self.settings)
            self.timer.setInterval(round(1000 / self.settings.ui_fps))
            self._notice("Preferências salvas. Os ajustes serão usados na próxima captura.")
        except (OSError, ValueError) as exc:
            self._notice(str(exc), True)

    def _export_settings(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar preferências", "beatlight-preferencias.json", "JSON (*.json)")
        if path:
            try:
                self.store.export(Path(path), self._current_settings())
                self._notice("Preferências exportadas.")
            except (OSError, ValueError) as exc:
                self._notice(str(exc), True)

    def _import_settings(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar preferências", "", "JSON (*.json)")
        if not path:
            return
        try:
            settings = self.store.import_file(Path(path))
            self.store.save(settings)
            self.settings = settings
            self.queue_spin.setValue(settings.queue_capacity)
            self.silence_spin.setValue(settings.silence_db)
            self.fps_spin.setValue(settings.ui_fps)
            load_dsp_settings(self, settings)
            load_kick_settings(self, settings)
            load_beat_settings(self, settings)
            load_lighting_settings(self, settings)
            self.link_use.setChecked(settings.sync_source == "link")
            self.link_offset.setValue(settings.link_offset_ms)
            self.block_combo.setCurrentIndex((256, 512, 1024, 2048).index(settings.block_size))
            self.runtime = self._make_runtime(settings)
            self.timer.setInterval(round(1000 / settings.ui_fps))
            self.source_combo.blockSignals(True)
            self.source_combo.setCurrentIndex(self.source_combo.findData(settings.source))
            self.source_combo.blockSignals(False)
            self.device_combo.clear()
            self._scan()
            self._notice("Preferências importadas e validadas.")
        except (OSError, ValueError, TypeError) as exc:
            self._notice(f"Não foi possível importar: {exc}", True)

    def _export_diagnostics(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar diagnóstico", "beatlight-diagnostico.json", "JSON (*.json)")
        if path:
            try:
                snapshot = self.runtime.snapshot()
                data = {"version": 1, "status": asdict(self.runtime.status()),
                        "snapshot": {k: v for k, v in asdict(snapshot).items() if k != "waveform"} if snapshot else None,
                        "lighting": asdict(self.light_runtime.snapshot()),
                        "link": asdict(self.link_runtime.snapshot()), "sync_options": self._sync_options,
                        "events": self.events.toPlainText()}
                Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                self._event("Diagnóstico exportado.")
            except OSError as exc:
                self._notice(str(exc), True)

    def _lighting_changed(self, *args):
        apply_lighting_controls(self)

    def _save_lighting_settings(self):
        try:
            settings = replace(self.settings, **lighting_form_values(self))
            self.store.save(settings)
            self.settings = settings
            self.light_notice.setText("Preferências de luz salvas. Ativação, controle manual e blackout são estados desta sessão.")
            self._event("Preferências de iluminação salvas.")
        except (OSError, ValueError) as exc:
            self.light_notice.setText(str(exc))

    def _export_lighting_states(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar estados abstratos", "beatlight-estados-luz.json", "JSON (*.json)")
        if path:
            try:
                data = {"version": 2, "color_model": "RGBW", "physical_output": False,
                        "fixtures": [asdict(f) for f in self.light_runtime.engine.fixtures],
                        "lighting": asdict(self.light_runtime.snapshot())}
                Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                self.light_notice.setText("Estados abstratos exportados.")
            except OSError as exc:
                self.light_notice.setText(str(exc))

    def _shutdown_runtimes(self):
        try:
            self.light_runtime.stop()
        finally:
            try:
                self.runtime.stop()
            finally:
                self.link_runtime.stop()

    def _finish_shutdown(self):
        if not self.pixel_page.closed_ready:
            QTimer.singleShot(25,self._finish_shutdown)
            return
        self.closed_ready=True
        self.close()

    def closeEvent(self, event: QCloseEvent):
        if self.closed_ready:
            self.timer.stop()
            self.executor.shutdown(wait=False)
            try:
                self.store.save(self._current_settings())
            except (OSError, ValueError):
                pass
            event.accept()
        else:
            event.ignore()
            self.closing = True
            self.pixel_page.shutdown()
            self.footer_status.setText("Encerrando áudio e iluminação…")
            if not self.busy:
                self._submit("shutdown", self._shutdown_runtimes)
