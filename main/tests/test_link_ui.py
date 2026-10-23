"""Integração do painel Link com os mesmos relógios do palco e da GUI."""
from dataclasses import replace
from time import monotonic
from test_ui import app, pump
from beatlight.configuration.store import Settings, SettingsStore, validate
from beatlight.sync.link import LinkSnapshot
from beatlight.ui.window import MainWindow
from beatlight.ui.lighting import can_sync_phrase


def test_link_panel_routes_clock_preserves_audio_and_returns_to_audio(app, tmp_path):
    store = SettingsStore(tmp_path / "prefs.json")
    window = MainWindow(store, Settings(source="synthetic", sync_source="link", light_effect="phrase_show"))
    window.show()
    try:
        pump(app, lambda: not window.busy and bool(window.devices))
        assert window.link_runtime.snapshot().state == "disabled"  # preferência não ingressa na rede
        window._navigate(8)
        assert window.page_title.text() == "Ableton Link"
        assert window.link_metrics["source"].text() == "ÁUDIO"
        window._start()
        pump(app, lambda: not window.busy and window.runtime.snapshot() is not None and window.runtime.snapshot().structure is not None)
        raw = window.runtime.snapshot()
        now = monotonic()
        window.link_runtime._publish(LinkSnapshot(now, "connected", 133, 24.1, 1, 2, .1))
        window._tick()
        assert window.link_metrics["source"].text() == "LINK"
        routed = window._effective_snapshot()
        assert routed.beat.bpm == 133 and routed.structure.phrase_kick == 1
        assert window.runtime.snapshot().timing_source == "audio"
        window._navigate(5)
        assert window.rhythm_badge.text() == "ABLETON LINK"
        window._navigate(7)
        window.stage_arm_button.click()
        assert can_sync_phrase(window)  # não depende de quatro kicks acústicos
        window._tick()
        window.stage_sync_button.click()
        assert window._phrase_sync_id == 1
        window.link_offset.setValue(35)
        assert window._sync_options == ("link", 35)
        window.link_runtime._publish(LinkSnapshot(monotonic(), "waiting", 133, 25, 0))
        window._tick()
        assert window._effective_snapshot().timing_source == "audio"
        window._navigate(8)
        assert window.link_metrics["source"].text() == "ÁUDIO"
    finally:
        window.close()
        pump(app, lambda: window.closed_ready)
    saved = store.load()
    assert saved.sync_source == "link" and saved.link_offset_ms == 35
    assert window.link_runtime.snapshot().state == "disabled"


def test_v12_migration_does_not_implicitly_activate_link():
    old = validate({"version": 12, "sync_source": "link", "link_offset_ms": 100,
        "light_mover_pattern": "double", "light_phrase_variation": "texture"})
    assert old.version == 13 and old.sync_source == "audio" and old.link_offset_ms == 0
    assert old.light_mover_pattern == "double" and old.light_phrase_variation == "texture"
