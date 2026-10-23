"""Integração de comandos da GUI com workers e snapshots, sem hardware."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from time import monotonic, sleep
import pytest
from PySide6.QtWidgets import QApplication, QFileDialog
from beatlight.configuration.store import Settings, SettingsStore
from beatlight.ui.theme import STYLE
from beatlight.ui.window import MainWindow


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    instance.setStyleSheet(STYLE)
    yield instance


def pump(app, condition, timeout=5):
    end = monotonic() + timeout
    while monotonic() < end:
        app.processEvents()
        if condition():
            return
        sleep(0.005)
    assert condition(), "Interface não completou a operação"


def test_capture_controls_and_async_shutdown(app, tmp_path):
    settings = Settings(source="synthetic")
    window = MainWindow(SettingsStore(tmp_path / "preferences.json"), settings)
    window.show()
    try:
        pump(app, lambda: not window.busy and bool(window.devices))
        assert window.start_button.isEnabled()
        window.start_button.click()
        pump(app, lambda: not window.busy and window.runtime.snapshot() is not None)
        window._tick()
        assert window.runtime.status().state == "running"
        assert not window.device_combo.isEnabled()
        assert window.stop_button.isEnabled()
        assert window.wave.snapshot is not None
        window.stop_button.click()
        pump(app, lambda: not window.busy and window.runtime.status().state == "stopped")
        assert window.device_combo.isEnabled()
        window._navigate(1)
        assert window.pages.currentIndex() == 1
        window._navigate(2)
        assert window.pages.currentIndex() == 2
    finally:
        window.close()
        pump(app, lambda: window.closed_ready)
    assert (tmp_path / "preferences.json").exists()


def test_import_preferences_replaces_runtime_and_source(app, tmp_path, monkeypatch):
    store = SettingsStore(tmp_path / "preferences.json")
    window = MainWindow(store, Settings(source="synthetic"))
    window.show()
    try:
        pump(app, lambda: not window.busy and bool(window.devices))
        imported = tmp_path / "import.json"
        store.export(imported, Settings(source="synthetic", block_size=1024, queue_capacity=4, ui_fps=45, fft_size=4096, fft_overlap=50, filter_mode="bandpass", kick_sensitivity=1.4, kick_refractory_ms=230, beat_min_bpm=100, beat_max_bpm=150, beat_hold_seconds=6, light_effect="ambient", light_master=0.6, light_palette="amber_violet"))
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(imported), "JSON"))
        window._import_settings()
        pump(app, lambda: not window.busy and bool(window.devices))
        assert window.block_combo.currentData() == 1024
        assert window.queue_spin.value() == 4
        assert window.settings.ui_fps == 45
        assert store.load().block_size == 1024
        assert window.fft_combo.currentData() == 4096
        assert window.overlap_combo.currentData() == 50
        assert window.filter_combo.currentData() == "bandpass"
        assert window.kick_spins["kick_sensitivity"].value() == 1.4
        window._start()
        pump(app, lambda: not window.busy and window.runtime.snapshot() is not None and window.runtime.snapshot().spectral is not None)
        assert window.runtime.snapshot().spectral.fft_size == 4096
        assert window.runtime.snapshot().spectral.filter_mode == "bandpass"
        assert window.runtime._analyzer_factory()._kicks.config.kick_refractory_ms == 230
        assert window.beat_spins["beat_hold_seconds"].value() == 6
        assert window.runtime._analyzer_factory()._beats.config.beat_min_bpm == 100
        assert window.light_effect_combo.currentData() == "ambient"
        assert window.light_runtime.controls().config.light_master == 0.6
        assert window.light_runtime.controls().config.light_palette == "amber_violet"
        assert not window.light_runtime.controls().armed
    finally:
        window.close()
        pump(app, lambda: window.closed_ready)


def test_spectral_page_controls_and_snapshot_rendering(app, tmp_path):
    window = MainWindow(SettingsStore(tmp_path / "preferences.json"), Settings(source="synthetic"))
    window.show()
    try:
        pump(app, lambda: not window.busy and bool(window.devices))
        window._navigate(3)
        assert window.nav_group.checkedId() == 3
        window.spectral_start.click()
        pump(app, lambda: not window.busy and window.runtime.snapshot() is not None and window.runtime.snapshot().spectral is not None)
        window._tick()
        assert window.spectrum_plot.snapshot is not None
        assert window.spectral_badge.text() == "AO VIVO"
        assert not window.fft_combo.isEnabled()
        assert window.spectral_metrics["rms"].text().endswith("dBFS")
        assert sum(bar.value() for bar in window.band_bars) == pytest.approx(1000, abs=2)
        window.spectral_stop.click()
        pump(app, lambda: not window.busy and window.runtime.status().state == "stopped")
        assert window.spectral_badge.text() == "ÚLTIMO RESULTADO"
    finally:
        window.close()
        pump(app, lambda: window.closed_ready)


def test_invalid_dsp_form_preserves_previous_runtime_and_settings(app, tmp_path):
    settings = Settings(source="synthetic")
    store = SettingsStore(tmp_path / "preferences.json")
    store.save(settings)
    window = MainWindow(store, settings)
    window.show()
    try:
        pump(app, lambda: not window.busy and bool(window.devices))
        window._navigate(2)
        prior = window.runtime
        window.filter_low_spin.setValue(500)  # corte superior continua 150 Hz
        window._apply_settings()
        assert window.runtime is prior
        assert window.settings == settings
        assert store.load() == settings
        assert "menor" in window.settings_notice.text()
    finally:
        window.close()
        pump(app, lambda: window.closed_ready)


def test_kick_page_live_events_stop_and_settings(app, tmp_path):
    settings = Settings(source="synthetic")
    store = SettingsStore(tmp_path / "preferences.json")
    window = MainWindow(store, settings)
    window.show()
    try:
        pump(app, lambda: not window.busy and bool(window.devices))
        window._navigate(4)
        assert window.nav_group.checkedId() == 4
        assert window.page_title.text() == "Kick Monitor"
        window.kick_start.click()
        pump(app, lambda: window.runtime.snapshot() is not None and
             window.runtime.snapshot().kicks is not None and window.runtime.snapshot().kicks.count >= 2)
        window._tick()
        assert window.kick_badge.text() == "AO VIVO"
        assert window.kick_table.rowCount() >= 2
        assert window.kick_metrics["count"].text() != "—"
        assert "TESTE SINTÉTICO" in window.kick_source.text()
        assert all(not widget.isEnabled() for widget in window.kick_widgets)
        window.kick_stop.click()
        pump(app, lambda: not window.busy and window.runtime.status().state == "stopped")
        assert window.kick_badge.text() == "ÚLTIMO RESULTADO"
        assert window.kick_indicator.text() == "PARADO"
        assert not window.kick_plot.active
        assert all(widget.isEnabled() for widget in window.kick_widgets)
        window._navigate(2)
        window.kick_spins["kick_sensitivity"].setValue(1.3)
        window._apply_settings()
        assert store.load().kick_sensitivity == 1.3
        assert window.runtime._analyzer_factory()._kicks.config.kick_sensitivity == 1.3
        prior = window.runtime
        window.kick_spins["kick_low_hz"].setValue(180)
        window._apply_settings()
        assert window.runtime is prior
        assert "Faixa de kick" in window.settings_notice.text()
        assert store.load().kick_low_hz == 40
    finally:
        window.close()
        pump(app, lambda: window.closed_ready)


def test_rhythm_monitor_acquires_freezes_and_saves_settings(app, tmp_path):
    store = SettingsStore(tmp_path / "preferences.json")
    window = MainWindow(store, Settings(source="synthetic"))
    window.show()
    try:
        pump(app, lambda: not window.busy and bool(window.devices))
        window._navigate(5)
        assert window.nav_group.checkedId() == 5
        assert window.page_title.text() == "Rhythm Monitor"
        window.rhythm_start.click()
        pump(app, lambda: window.runtime.snapshot() is not None and
             window.runtime.snapshot().beat is not None and window.runtime.snapshot().beat.state == "locked", timeout=8)
        window._tick()
        assert window.rhythm_badge.text() == "SINCRONIZADO"
        assert float(window.rhythm_metrics["bpm"].text()) == pytest.approx(120, abs=1)
        assert window.beat_clock.active
        assert all(not widget.isEnabled() for widget in window.beat_widgets)
        window.rhythm_stop.click()
        pump(app, lambda: not window.busy and window.runtime.status().state == "stopped")
        window._tick()
        phase = window.beat_clock.snapshot.phase
        assert not window.beat_clock.active
        assert "PARADO" in window.rhythm_badge.text()
        sleep(0.05)
        window._tick()
        assert window.beat_clock.snapshot.phase == phase
        window._navigate(2)
        window.beat_spins["beat_hold_seconds"].setValue(5)
        window._apply_settings()
        assert store.load().beat_hold_seconds == 5
        assert window.runtime._analyzer_factory()._beats.config.beat_hold_seconds == 5
        prior = window.runtime
        window.beat_spins["beat_min_bpm"].setValue(180)
        window._apply_settings()
        assert window.runtime is prior
        assert "Faixa de BPM" in window.settings_notice.text()
        assert store.load().beat_min_bpm == 90
    finally:
        window.close()
        pump(app, lambda: window.closed_ready)


def test_rhythm_projection_expires_without_callbacks_and_clears_hypotheses(app, tmp_path, monkeypatch, block_factory):
    from dataclasses import replace
    from beatlight.contracts import KickEvent
    from beatlight.dsp.pipeline import AudioAnalyzer
    from beatlight.music.tracker import BeatTracker
    from beatlight.ui.rhythm import update_rhythm_view
    window = MainWindow(SettingsStore(tmp_path / "preferences.json"), Settings(source="synthetic"))
    window.show()
    try:
        pump(app, lambda: not window.busy and bool(window.devices))
        tracker = BeatTracker()
        start = monotonic() - 8
        for i in range(12):
            t = start + i * 0.5
            beat = tracker.process((KickEvent(t, t + 0.02, 1, 0.95),), t + 0.03)
        snapshot = AudioAnalyzer().process(block_factory([[0, 0]] * 512))
        snapshot = replace(snapshot, beat=beat)
        status = replace(window.runtime.status(), state="running", audio_age=1.6)
        window._navigate(5)
        monkeypatch.setattr("beatlight.ui.rhythm.monotonic", lambda: beat.last_reference_at + 1.6)
        update_rhythm_view(window, snapshot, status)
        assert window.rhythm_badge.text() == "ESTIMADO"
        assert "Sem novos blocos" in window.rhythm_detail.text()
        assert window.beat_clock.active
        monkeypatch.setattr("beatlight.ui.rhythm.monotonic", lambda: beat.expires_at + 0.1)
        update_rhythm_view(window, snapshot, status)
        assert window.rhythm_badge.text() == "SEM SINCRONISMO"
        assert not window.beat_clock.active
        assert window.rhythm_metrics["next"].text() == "—"
        assert all(value.text() == "—" for value, detail in window.rhythm_hypotheses)
        tracker.reset()
        empty = tracker.process((), beat.expires_at + 1)
        update_rhythm_view(window, replace(snapshot, beat=empty), status)
        assert all(value.text() == "—" for value, detail in window.rhythm_hypotheses)
    finally:
        window.close()
        pump(app, lambda: window.closed_ready)


def test_lighting_controls_blackout_export_and_shutdown(app, tmp_path, monkeypatch):
    import json
    store = SettingsStore(tmp_path / "preferences.json")
    settings = Settings(source="synthetic", light_transition_ms=0)
    window = MainWindow(store, settings)
    window.show()
    try:
        pump(app, lambda: not window.busy and bool(window.devices))
        window._navigate(6)
        assert window.nav_group.checkedId() == 6
        assert window.page_title.text() == "Lighting Studio"
        assert window.light_table.rowCount() == 6
        assert not window.light_runtime.controls().armed
        window.light_effect_combo.setCurrentIndex(window.light_effect_combo.findData("ambient"))
        window.light_arm_check.setChecked(True)
        pump(app, lambda: window.light_runtime.snapshot().status == "ambient")
        window._tick()
        assert any(bar.value() > 0 for row, fixture, bar in window.light_rows.values())
        window.light_manual_check.setChecked(True)
        window.light_manual_spins["manual_pan"].setValue(80)
        pump(app, lambda: window.light_runtime.snapshot().status == "manual" and
             window.light_runtime.snapshot().states[-1].pan == 0.8)
        window.light_blackout_button.click()
        pump(app, lambda: window.light_runtime.snapshot().status == "blackout")
        window._tick()
        assert all(bar.value() == 0 for row, fixture, bar in window.light_rows.values())
        window.light_effect_combo.setCurrentIndex(window.light_effect_combo.findData("beat_chase"))
        window.light_spins["light_master"].setValue(60)
        assert window.light_blackout_button.isChecked()
        pump(app, lambda: window.light_runtime.snapshot().master == 0.6)
        assert all(s.intensity == 0 for s in window.light_runtime.snapshot().states)
        window._save_lighting_settings()
        assert store.load().light_master == 0.6
        assert store.load().light_effect == "beat_chase"
        exported = tmp_path / "states.json"
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(exported), "JSON"))
        window._export_lighting_states()
        data = json.loads(exported.read_text(encoding="utf-8"))
        assert data["version"] == 2 and data["color_model"] == "RGBW"
        assert all("white" in s for s in data["lighting"]["states"])
        assert not data["physical_output"]
        assert len(data["fixtures"]) == 6
        assert data["lighting"]["blackout"]
        window.light_blackout_button.click()
        pump(app, lambda: window.light_runtime.snapshot().status == "manual")
    finally:
        window.close()
        pump(app, lambda: window.closed_ready)
    assert not window.light_runtime.running
    assert all(s.intensity == 0 for s in window.light_runtime.snapshot().states)
    # Estados operacionais não são reativados por preferências salvas.
    reopened = MainWindow(store, store.load())
    try:
        assert not reopened.light_runtime.controls().armed
        assert not reopened.light_runtime.controls().manual
        assert not reopened.light_runtime.controls().blackout
    finally:
        reopened.close()
        pump(app, lambda: reopened.closed_ready)


def test_light_controls_do_not_replace_running_audio(app, tmp_path):
    window = MainWindow(SettingsStore(tmp_path / "preferences.json"), Settings(source="synthetic"))
    window.show()
    try:
        pump(app, lambda: not window.busy and bool(window.devices))
        window._start()
        pump(app, lambda: window.runtime.snapshot() is not None)
        original = window.runtime
        window.light_arm_check.setChecked(True)
        window.light_spins["light_master"].setValue(50)
        window._save_lighting_settings()
        window._tick()
        assert window.runtime is original
        assert window.runtime.status().state == "running"
        assert window.light_spins["light_master"].isEnabled()
        assert not window.fft_combo.isEnabled()
    finally:
        window.close()
        pump(app, lambda: window.closed_ready)


def test_stage_shares_controls_renders_live_states_and_blackout(app, tmp_path):
    window = MainWindow(SettingsStore(tmp_path / "preferences.json"), Settings(source="synthetic", light_transition_ms=0))
    window.show()
    try:
        pump(app, lambda: not window.busy and bool(window.devices))
        window._navigate(7)
        assert window.nav_group.checkedId() == 7
        assert window.page_title.text() == "Stage Preview"
        window.stage_music_button.click()
        assert window.light_effect_combo.currentData() == "musical"
        window.stage_show_button.click()
        assert window.light_effect_combo.currentData() == "phrase_show"
        assert window.light_runtime.controls().config.light_effect == "phrase_show"
        window.light_effect_combo.setCurrentIndex(window.light_effect_combo.findData("ambient"))
        window.stage_arm_button.click()
        pump(app, lambda: window.light_runtime.snapshot().status == "ambient")
        window._tick()
        assert window.stage_view.snapshot.states == window.light_runtime.snapshot().states
        bright = window.stage_view.grab().toImage()
        window.stage_blackout_button.click()
        pump(app, lambda: window.light_runtime.snapshot().status == "blackout")
        window._tick()
        assert window.light_blackout_button.isChecked()
        assert all(s.intensity == 0 for s in window.stage_view.snapshot.states)
        dark = window.stage_view.grab().toImage()
        assert bright != dark
        window._navigate(6)
        window.light_blackout_button.click()
        window._navigate(7)
        assert not window.stage_blackout_button.isChecked()
        window.resize(1100, 760)
        app.processEvents()
        scroll = window.pages.widget(7)
        assert scroll.verticalScrollBar().maximum() > 0
    finally:
        window.close()
        pump(app, lambda: window.closed_ready)
    assert not window.light_runtime.running


def test_structure_demo_source_survives_preferences_and_remains_explicitly_synthetic(app, tmp_path):
    store = SettingsStore(tmp_path / "preferences.json")
    settings = Settings(source="structure_demo", light_effect="musical")
    store.save(settings)
    window = MainWindow(store, store.load())
    window.show()
    try:
        pump(app, lambda: not window.busy and bool(window.devices))
        assert window.source_combo.currentData() == "structure_demo"
        assert window._source().structure_demo
        window._navigate(7)
        window._start()
        pump(app, lambda: window.runtime.snapshot() is not None and window.runtime.snapshot().structure is not None)
        window._tick()
        assert "TESTE SINTÉTICO" in window.light_source.text()
        assert "TESTE SINTÉTICO" in window.notice.text()
        assert window.structure_metrics["state"].text() == "ANALISANDO"
        window._navigate(4)
        assert "TESTE SINTÉTICO" in window.kick_source.text()
        window.stage_arm_button.setChecked(False)
        assert not window.light_runtime.controls().armed
    finally:
        window.close()
        pump(app, lambda: window.closed_ready)


def test_stage_reprojects_pan_and_tilt_from_fixture_states_only(app):
    from dataclasses import replace
    from beatlight.contracts import LightingInput
    from beatlight.lighting.config import LightingControls
    from beatlight.lighting.engine import LightingEngine
    from beatlight.ui.stage import StageView
    engine = LightingEngine()
    view = StageView(engine.fixtures)
    controls = LightingControls(armed=True, manual=True, manual_pan=0.2, manual_tilt=0.2)
    frame = engine.render(LightingInput(), controls, 1)
    a = view.beam_target(4, "moving_head", frame.states[4])
    b = view.beam_target(4, "moving_head", replace(frame.states[4], pan=0.8, tilt=0.8))
    assert b.x() > a.x() and b.y() > a.y()
    view.set_snapshot(frame)
    assert view.snapshot is frame
    view.close()


@pytest.mark.parametrize("size", [(1440, 960), (1280, 800), (1100, 760)])
def test_stage_geometry_stays_fixed_across_structure_labels(app, tmp_path, size, monkeypatch, block_factory):
    from dataclasses import replace
    from beatlight.contracts import StructureSnapshot
    from beatlight.dsp.pipeline import AudioAnalyzer
    from beatlight.ui.stage import update_stage_view
    window = MainWindow(SettingsStore(tmp_path / "preferences.json"), Settings(source="synthetic"))
    window.resize(*size)
    window.show()
    try:
        pump(app, lambda: not window.busy and bool(window.devices))
        window._navigate(7)
        # Mantém as fontes paradas: somente os descritores da apresentação mudam.
        window.timer.stop()
        base = AudioAnalyzer().process(block_factory([[0, 0]] * 2048))
        status = replace(window.runtime.status(), state="running", audio_age=0)
        light = window.light_runtime.snapshot()
        geometry = []
        viewport = []
        for state, text in [("warming", "Aprendendo o groove: precisa de BPM confiável e ao menos oito kicks."),
            ("groove", "Groove; contagem relativa de oito kicks, assumindo 4/4."),
            ("breakdown", "Breakdown: ausência de kicks e redução dos graves; procurando sinais de tensão."),
            ("buildup", "Build-up: ataques repetidos com aceleração ou crescimento dos agudos."),
            ("drop", "Retorno do kick e dos graves; alta energia no kick 8/8."),
            ("warming", "Aguardando referência. " * 12)]:
            m = StructureSnapshot(10, state, 0.95, 0.85, 0.5, 0.5, 8, 12, 8, 4, 2, 8, 1, 9.9, 9.9, 0.5, text, ())
            monkeypatch.setattr(window.light_runtime, "snapshot", lambda reason=text: replace(light, reason=reason))
            update_stage_view(window, replace(base, structure=m), status, 10)
            for _ in range(5):
                app.processEvents()
                geometry.append(window.stage_view.geometry().getRect())
                viewport.append(window.pages.widget(7).viewport().size().toTuple())
        assert len(set(geometry)) == 1, sorted(set(geometry))
        assert len(set(viewport)) == 1, sorted(set(viewport))
    finally:
        window.close()
        pump(app, lambda: window.closed_ready)


def test_auto_color_choice_is_shared_saved_and_does_not_replace_audio_runtime(app, tmp_path):
    store = SettingsStore(tmp_path / "preferences.json")
    window = MainWindow(store, Settings(source="synthetic"))
    window.show()
    try:
        pump(app, lambda: not window.busy and bool(window.devices))
        window._navigate(7)
        window._start()
        pump(app, lambda: window.runtime.snapshot() is not None)
        original = window.runtime
        assert window.stage_auto_colors.isChecked()
        window.stage_auto_colors.setChecked(False)
        window._tick()
        assert window.light_color_combo.currentData() == "fixed"
        assert window.light_palette_combo.isEnabled()
        window._save_lighting_settings()
        assert store.load().light_color_mode == "fixed"
        window.light_color_combo.setCurrentIndex(window.light_color_combo.findData("automatic"))
        window._tick()
        assert window.stage_auto_colors.isChecked()
        assert not window.light_palette_combo.isEnabled()
        assert window.runtime is original and original.status().state == "running"
    finally:
        window.close()
        pump(app, lambda: window.closed_ready)


def test_bass_density_controls_and_demo_are_shared_saved_and_keep_capture_running(app,tmp_path):
    store=SettingsStore(tmp_path/"preferences.json")
    window=MainWindow(store,Settings(source="texture_demo",light_effect="bass_flow",light_transition_ms=0))
    window.show()
    try:
        pump(app,lambda:not window.busy and bool(window.devices))
        assert window._source().texture_demo
        assert window.light_spins["light_kick_weight"].value()==70
        assert window.light_spins["light_bass_weight"].value()==65
        assert window.light_spins["light_density_weight"].value()==50
        assert window.light_runtime.controls().config.light_bass_weight==0.65
        window._navigate(7)
        window._start()
        window.light_arm_check.setChecked(True)
        pump(app,lambda:window.runtime.snapshot() is not None and window.runtime.snapshot().texture is not None)
        window._tick()
        assert "TESTE SINTÉTICO" in window.notice.text()
        assert any(bar.value()>0 for bar in window.texture_meters.values())
        original=window.runtime
        window.light_spins["light_bass_weight"].setValue(85)
        window.light_spins["light_density_weight"].setValue(70)
        window.light_effect_combo.setCurrentIndex(window.light_effect_combo.findData("density_wash"))
        window._save_lighting_settings()
        assert store.load().light_bass_weight==0.85 and store.load().light_density_weight==0.7
        assert store.load().source=="texture_demo" and store.load().light_effect=="density_wash"
        from beatlight.ui.lighting import load_lighting_settings
        load_lighting_settings(window,store.load())
        assert window.light_spins["light_bass_weight"].value()==85
        assert window.light_runtime.controls().config.light_density_weight==0.7
        assert window.runtime is original and original.status().state=="running"
        window._navigate(4)
        window._tick()
        assert window.kick_table.columnCount()==5
    finally:
        window.close()
        pump(app,lambda:window.closed_ready)


def test_stage_and_rhythm_project_same_grid_without_new_kicks(app, tmp_path, monkeypatch, block_factory):
    from dataclasses import replace
    from beatlight.contracts import KickEvent, StructureSnapshot
    from beatlight.dsp.pipeline import AudioAnalyzer
    from beatlight.music.grid import KickGrid
    from beatlight.ui.stage import update_stage_view
    from beatlight.ui.rhythm import update_rhythm_view
    window = MainWindow(SettingsStore(tmp_path / "preferences.json"), Settings(source="synthetic"))
    window.show()
    try:
        pump(app, lambda: not window.busy and bool(window.devices))
        window.timer.stop()
        window._navigate(7)
        grid = KickGrid()
        for i in range(4):
            grid.observe(KickEvent(100 + i * 0.5, 100 + i * 0.5, 1, 0.95))
        base = AudioAnalyzer().process(block_factory([[0, 0]] * 2048))
        status = replace(window.runtime.status(), state="running", audio_age=0)
        cells, geometry = set(), set()
        for i in range(8):
            at = 102.1 + i * 0.5
            # Campo legado congelado: a apresentação deve derivar a frase do relógio.
            structure = StructureSnapshot(at, "breakdown", 0.3, 0.7, 0.3, 0.3, 0, at - 101.5,
                1, 1, 1, 0, 0, None, 101.5, 0.5, "teste", (), grid=grid.snapshot(at))
            snapshot = replace(base, structure=structure, beat=None)
            monkeypatch.setattr("beatlight.ui.rhythm.monotonic", lambda at=at: at)
            update_stage_view(window, snapshot, status, at)
            update_rhythm_view(window, snapshot, status)
            app.processEvents()
            active = [j for j, cell in enumerate(window.phrase_cells) if cell.property("phrase_active")]
            assert len(active) == 1
            cells.add(active[0])
            assert window.grid_phase_bar.value() == round(window.beat_clock.snapshot.phase * 1000)
            assert window.rhythm_grid.grid.beat_index == grid.snapshot(at).beat_index
            geometry.add(window.stage_view.geometry().getRect())
        assert cells == set(range(8))
        assert len(geometry) == 1
    finally:
        window.close()
        pump(app, lambda: window.closed_ready)


def test_rgbw_manual_controls_table_and_new_preferences(app, tmp_path):
    store = SettingsStore(tmp_path / "rgbw.json")
    window = MainWindow(store, Settings(source="synthetic", light_transition_ms=0))
    window.show()
    try:
        pump(app, lambda: not window.busy and bool(window.devices))
        window._navigate(6)
        window.light_spins["light_white_strength"].setValue(40)
        window.light_spins["light_show_complexity"].setValue(90)
        window.stage_show_button.click()
        window._save_lighting_settings()
        assert store.load().version == 13
        assert store.load().light_white_strength == .4
        assert store.load().light_show_complexity == .9
        assert store.load().light_effect == "phrase_show"
        window.light_manual_check.setChecked(True)
        window.light_rgbw_check.setChecked(True)
        for key, value in (("manual_red",0), ("manual_green",0), ("manual_blue",0), ("manual_white",100)):
            window.light_manual_spins[key].setValue(value)
        window.light_arm_check.setChecked(True)
        pump(app, lambda: all(s.white == 1 for s in window.light_runtime.snapshot().states))
        window._tick()
        assert window.light_table.item(0,6).text() == "100%"
        assert window.light_table.item(0,3).background().color().name() == "#ffffff"
        assert window.light_runtime.snapshot().states[0].color == (0,0,0)
        window.light_blackout_button.setChecked(True)
        pump(app, lambda: window.light_runtime.snapshot().status == "blackout")
        assert all(s.white == s.intensity == 0 for s in window.light_runtime.snapshot().states)
    finally:
        window.close()
        pump(app, lambda: window.closed_ready)


def test_phrase_sync_button_aligns_lights_without_restarting_audio_or_saving_click(app,tmp_path):
    import json
    store=SettingsStore(tmp_path/"cycles.json")
    window=MainWindow(store,Settings(source="structure_demo",light_transition_ms=0))
    window.show()
    try:
        pump(app,lambda:not window.busy and bool(window.devices))
        window._navigate(7)
        assert window.light_variation_combo.currentData()=="texture"
        window.stage_phrase_button.click()
        assert window.light_effect_combo.currentData()=="phrase_show"
        assert not window.stage_sync_button.isEnabled()
        window._start()
        window.stage_arm_button.click()
        pump(app,lambda:window.stage_sync_button.isEnabled(),timeout=6)
        # Mesmo vindo do show antigo, o clique deve ativar e alinhar o novo modo.
        window.light_effect_combo.setCurrentIndex(window.light_effect_combo.findData("orchestrated_show"))
        window._tick()
        assert window.stage_sync_button.isEnabled()
        assert window.stage_sync_button.geometry().top() < window.stage_view.geometry().top()
        assert window.phrase_cells[0].geometry().top() < window.stage_view.geometry().top()
        runtime=window.runtime
        origin=runtime.snapshot().structure.grid.phrase_origin
        window.stage_sync_button.click()
        command=window.light_runtime.controls().phrase_sync_id
        assert command==1
        assert window.light_effect_combo.currentData()=="phrase_show"
        pump(app,lambda:window.light_runtime.snapshot().phrase_synced)
        light=window.light_runtime.snapshot()
        assert light.phrase_step==1 and light.phrase_sync_id==command
        assert window.runtime is runtime and runtime.status().state=="running"
        assert runtime.snapshot().structure.grid.phrase_origin==origin
        window._tick()
        assert window.phrase_cells[0].property("phrase_active")
        assert "alinhado pelo clique" in window.stage_phrase_info.text()
        window.light_pattern_combo.setCurrentIndex(window.light_pattern_combo.findData("chase"))
        window.light_prepare_combo.setCurrentIndex(window.light_prepare_combo.findData("blackout"))
        window.light_variation_combo.setCurrentIndex(window.light_variation_combo.findData("cycle"))
        window._save_lighting_settings()
        saved=store.load()
        assert saved.light_phrase_variation=="cycle"
        assert saved.light_phrase_pattern=="chase" and saved.light_phrase_prepare=="blackout"
        assert "phrase_sync_at" not in json.loads(store.path.read_text())
    finally:
        window.close()
        pump(app,lambda:window.closed_ready)


def test_show_eight_toggle_changes_effect_and_stage_pattern_selector_is_shared(app,tmp_path):
    window=MainWindow(SettingsStore(tmp_path/"toggles.json"),Settings(source="synthetic",light_effect="phrase_show"))
    window.show()
    try:
        pump(app,lambda:not window.busy and bool(window.devices))
        window._navigate(7)
        assert window.stage_show_button.isChecked()
        window.stage_show_button.click()
        assert window.light_effect_combo.currentData()=="orchestrated_show"
        window.stage_show_button.click()
        assert window.light_effect_combo.currentData()=="phrase_show"
        window.stage_pattern_combo.setCurrentIndex(window.stage_pattern_combo.findData("heartbeat"))
        assert window.light_runtime.controls().config.light_phrase_pattern=="heartbeat"
        window.light_pattern_combo.setCurrentIndex(window.light_pattern_combo.findData("syncopated"))
        window._tick()
        assert window.stage_pattern_combo.currentData()=="syncopated"
        window.light_spins["light_change_sensitivity"].setValue(150)
        window._save_lighting_settings()
        assert window.store.load().light_change_sensitivity==1.5
    finally:
        window.close()
        pump(app,lambda:window.closed_ready)


def test_par_pattern_preview_renders_different_rhythms_from_snapshot_only(app):
    from dataclasses import replace
    from beatlight.lighting.engine import LightingEngine
    from beatlight.lighting.config import LightConfig,LightingControls
    from beatlight.ui.stage import ParPatternView
    from test_rhythmic_show import music
    view=ParPatternView()
    view.resize(700,76)
    view.show()
    c=LightingControls(LightConfig(light_effect="phrase_show",light_transition_ms=0,light_phrase_pattern="chase"),armed=True)
    a=LightingEngine().render(music(0),c,0)
    b=LightingEngine().render(music(0),replace(c,config=replace(c.config,light_phrase_pattern="heartbeat")),0)
    view.set_snapshot(a)
    app.processEvents()
    first=view.grab().toImage()
    view.set_snapshot(b)
    app.processEvents()
    assert first!=view.grab().toImage() and view.snapshot is b
    view.close()


def test_mover_and_calm_controls_share_settings_and_preserve_audio_runtime(app,tmp_path):
    store=SettingsStore(tmp_path/"calm.json")
    window=MainWindow(store,Settings(source="synthetic",light_effect="phrase_show"))
    window.show()
    try:
        pump(app,lambda:not window.busy and bool(window.devices))
        window._start()
        pump(app,lambda:window.runtime.snapshot() is not None)
        runtime=window.runtime
        window.light_mover_combo.setCurrentIndex(window.light_mover_combo.findData("double"))
        window.light_breakdown_combo.setCurrentIndex(window.light_breakdown_combo.findData("crossfade"))
        window._save_lighting_settings()
        saved=store.load()
        assert saved.version == 13 and saved.light_mover_pattern=="double" and saved.light_breakdown_style=="crossfade"
        assert window.light_runtime.controls().config.light_mover_pattern=="double"
        assert window.runtime is runtime and runtime.status().state=="running"
    finally:
        window.close()
        pump(app,lambda:window.closed_ready)


def test_calm_preview_shows_continuous_light_instead_of_grid_blocks(app):
    from dataclasses import replace
    from beatlight.lighting.engine import LightingEngine
    from beatlight.lighting.config import LightConfig,LightingControls
    from beatlight.ui.stage import ParPatternView
    from test_rhythmic_show import music
    view=ParPatternView()
    view.resize(700,76)
    view.show()
    c=LightingControls(LightConfig(light_effect="phrase_show",light_transition_ms=0),armed=True)
    calm=LightingEngine().render(music(0,state="breakdown",tension=.2),c,0)
    view.set_snapshot(calm)
    app.processEvents()
    fade=view.grab().toImage()
    dense=LightingEngine().render(music(0,state="breakdown",tension=.8),c,0)
    view.set_snapshot(dense)
    app.processEvents()
    assert fade!=view.grab().toImage() and calm.breakdown_calm and not dense.breakdown_calm
    view.close()
