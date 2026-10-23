import json
from dataclasses import replace
import pytest
from beatlight.configuration.store import Settings, SettingsStore, validate


def test_preferences_round_trip_and_atomic_cleanup(tmp_path):
    store = SettingsStore(tmp_path / "preferences.json")
    settings = replace(Settings(), block_size=1024, source="synthetic")
    store.save(settings)
    assert store.load() == settings
    assert not list(tmp_path.glob("*.tmp"))


def test_corrupt_preferences_fall_back_without_losing_original(tmp_path):
    path = tmp_path / "preferences.json"
    path.write_text("invalid JSON", encoding="utf-8")
    store = SettingsStore(path)
    assert store.load() == Settings()
    assert store.warning
    assert path.read_text() == "invalid JSON"


@pytest.mark.parametrize("data", [[], {"version": 14}, {"block_size": 513},
    {"silence_db": float("nan")}, {"queue_capacity": True}, {"ui_fps": 0},
    {"device_id": 32}, {"version": True}, {"source": "unknown"}])
def test_invalid_settings_rejected(data):
    with pytest.raises(ValueError):
        validate(data)


def test_import_validates_version(tmp_path):
    path = tmp_path / "import.json"
    path.write_text(json.dumps({"version": 22}))
    with pytest.raises(ValueError):
        SettingsStore.import_file(path)


def test_v1_preferences_migrate_without_losing_capture_settings(tmp_path):
    path = tmp_path / "preferences.json"
    path.write_text(json.dumps({"version": 1, "source": "wasapi", "device_id": "saved:realtek",
                                "block_size": 1024, "queue_capacity": 12, "silence_db": -70, "ui_fps": 45,
                                "fft_size": 777}))  # campo desconhecido no esquema antigo
    store = SettingsStore(path)
    settings = store.load()
    assert settings.version == 13
    assert settings.device_id == "saved:realtek"
    assert settings.block_size == 1024
    assert settings.queue_capacity == 12
    assert settings.fft_size == 2048
    assert not store.warning
    assert json.loads(path.read_text())["version"] == 1  # carregar não sobrescreve o original
    store.save(settings)
    assert json.loads(path.read_text())["version"] == 13


def test_invalid_dsp_preferences_fall_back(tmp_path):
    path = tmp_path / "preferences.json"
    path.write_text(json.dumps({"version": 2, "fft_size": 777}))
    store = SettingsStore(path)
    assert store.load() == Settings()
    assert "FFT" in store.warning


def test_v2_migration_preserves_dsp_and_defaults_unknown_kick_fields():
    settings = validate({"version": 2, "fft_size": 4096, "filter_mode": "bandpass",
                         "filter_low_hz": 50, "filter_high_hz": 180,
                         "kick_sensitivity": "unknown-before-v3"})
    assert settings.version == 13
    assert settings.fft_size == 4096
    assert settings.filter_high_hz == 180
    assert settings.kick_sensitivity == 1.0


def test_v3_kick_preferences_validated_and_round_tripped(tmp_path):
    store = SettingsStore(tmp_path / "preferences.json")
    settings = replace(Settings(), kick_sensitivity=1.4, kick_refractory_ms=220, kick_low_hz=35)
    store.save(settings)
    assert store.load() == settings
    with pytest.raises(ValueError, match="Sensibilidade"):
        validate({"version": 3, "kick_sensitivity": 10})


def test_v3_migration_preserves_user_kick_tuning():
    settings = validate({"version": 3, "device_id": "realtek:saved", "kick_sensitivity": 1.3,
        "kick_low_hz": 35, "kick_high_hz": 180, "fft_size": 4096,
        "beat_min_bpm": "unknown-before-v4"})
    assert settings.version == 13
    assert settings.kick_sensitivity == 1.3
    assert settings.kick_low_hz == 35
    assert settings.device_id == "realtek:saved"
    assert settings.fft_size == 4096
    assert settings.beat_min_bpm == 90


def test_v4_tempo_settings_validated_and_round_tripped(tmp_path):
    store = SettingsStore(tmp_path / "preferences.json")
    settings = replace(Settings(), beat_min_bpm=100, beat_max_bpm=150, beat_hold_seconds=6)
    store.save(settings)
    assert store.load() == settings
    with pytest.raises(ValueError, match="Faixa de BPM"):
        validate({"version": 4, "beat_min_bpm": 170})


def test_v4_migration_preserves_validated_audio_kick_and_tempo_preferences():
    settings = validate({"version": 4, "device_id": "realtek:saved", "kick_sensitivity": 1.3,
        "fft_size": 4096, "beat_min_bpm": 100, "beat_max_bpm": 150, "beat_hold_seconds": 6,
        "light_effect": "unknown-before-v5"})
    assert settings.version == 13
    assert settings.device_id == "realtek:saved"
    assert settings.kick_sensitivity == 1.3
    assert settings.fft_size == 4096
    assert settings.beat_min_bpm == 100 and settings.beat_hold_seconds == 6
    assert settings.light_effect == "kick_pulse"


def test_lighting_preferences_round_trip_and_invalid_values_rejected(tmp_path):
    settings = replace(Settings(), light_effect="ambient", light_master=0.6, light_palette="amber_violet")
    store = SettingsStore(tmp_path / "preferences.json")
    store.save(settings)
    assert store.load() == settings
    with pytest.raises(ValueError, match="Master"):
        validate({"version": 5, "light_master": 2})


def test_v6_preferences_migrate_without_losing_color_choice_or_audio_tuning():
    s=validate(dict(version=6,source="wasapi",light_color_mode="fixed",light_palette="red_blue",kick_sensitivity=1.3))
    assert s.version == 13 and s.light_color_mode=="fixed" and s.light_palette=="red_blue"
    assert s.kick_sensitivity==1.3 and s.light_bass_weight==0.65
    with pytest.raises(ValueError,match="Pesos"):
        validate(dict(version=7,light_density_weight=2))
