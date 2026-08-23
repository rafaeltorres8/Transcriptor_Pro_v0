import json
import pytest
from core.config import AppConfig, DEFAULT_FORMATS, load_config, save_config

def test_default_config_has_expected_defaults():
    config = AppConfig()
    assert config.ffmpeg_path == ""
    assert config.last_model == "base"
    assert config.output_formats == list(DEFAULT_FORMATS)

def test_save_and_load_roundtrip(tmp_path):
    config_path = tmp_path / "config.json"
    original = AppConfig(
        ffmpeg_path="/usr/bin/ffmpeg",
        last_model="small",
        output_formats=["txt", "srt"],
        last_output_dir="/home/user/out",
    )

    assert save_config(original, path=config_path) is True
    loaded = load_config(path=config_path)

    assert loaded == original

def test_load_config_missing_file_returns_defaults(tmp_path):
    config_path = tmp_path / "does_not_exist.json"
    loaded = load_config(path=config_path)
    assert loaded == AppConfig()

def test_load_config_corrupted_json_returns_defaults(tmp_path):
    config_path = tmp_path / "corrupt.json"
    config_path.write_text("{not valid json!!", encoding="utf-8")

    loaded = load_config(path=config_path)
    assert loaded == AppConfig()

def test_load_config_invalid_model_is_sanitized(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"last_model": "not-a-real-model"}), encoding="utf-8"
    )

    loaded = load_config(path=config_path)
    assert loaded.last_model == "base"

def test_load_config_invalid_formats_are_filtered(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"output_formats": ["txt", "bogus", "srt"]}), encoding="utf-8"
    )

    loaded = load_config(path=config_path)
    assert loaded.output_formats == ["txt", "srt"]

def test_load_config_all_invalid_formats_falls_back_to_default(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"output_formats": ["bogus"]}), encoding="utf-8")

    loaded = load_config(path=config_path)
    assert loaded.output_formats == list(DEFAULT_FORMATS)

def test_save_config_creates_parent_directories(tmp_path):
    nested_path = tmp_path / "nested" / "dir" / "config.json"
    config = AppConfig(ffmpeg_path="ffmpeg")

    assert save_config(config, path=nested_path) is True
    assert nested_path.exists()

def test_save_config_handles_oserror(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    config = AppConfig()

    def broken_mkdir(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(config_path.parent.__class__, "mkdir", broken_mkdir)
    assert save_config(config, path=config_path) is False

def test_from_dict_ignores_unknown_keys():
    config = AppConfig.from_dict({"ffmpeg_path": "ffmpeg", "unknown_key": 123})
    assert config.ffmpeg_path == "ffmpeg"
    assert not hasattr(config, "unknown_key")
