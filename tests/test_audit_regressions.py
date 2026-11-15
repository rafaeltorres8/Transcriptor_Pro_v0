import json
import sys
import types
from importlib import import_module
from unittest.mock import MagicMock

import pytest

from core.config import AppConfig, load_config, save_config
from core.transcriber import transcribe_audio


@pytest.mark.parametrize('data', [[], None, 42, 'text', {'output_formats': None},
                                      {'output_formats': [[], 'txt']}, {'ffmpeg_path': 42}])
def test_malformed_preferences_are_safe(tmp_path, data):
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    config = load_config(path)
    assert isinstance(config, AppConfig)
    assert isinstance(config.ffmpeg_path, str)
    assert isinstance(config.output_formats, list)


def test_non_utf8_preferences_use_defaults(tmp_path):
    path = tmp_path / 'config.json'
    path.write_bytes(b'\xff\xfe')
    assert load_config(path) == AppConfig()


def test_failed_preference_save_preserves_previous_file(tmp_path, monkeypatch):
    import core.config as config

    path = tmp_path / 'config.json'
    path.write_text('{"last_model":"tiny"}', encoding='utf-8')
    original = path.read_bytes()

    def fail(*args, **kwargs):
        raise OSError('disk full')

    monkeypatch.setattr(config.json, 'dump', fail)
    assert save_config(AppConfig(), path) is False
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


def test_progress_uses_submodule_when_package_exports_function(monkeypatch):
    # Whisper exports a function named transcribe at package level.
    from tqdm import tqdm

    module = types.ModuleType('whisper.transcribe')
    module.tqdm = types.SimpleNamespace(tqdm=tqdm)
    package = types.ModuleType('whisper')
    package.transcribe = lambda: None
    monkeypatch.setitem(sys.modules, 'whisper', package)
    monkeypatch.setitem(sys.modules, 'whisper.transcribe', module)
    reported = []

    def run(path, fp16, verbose=None):
        assert verbose is False
        bar_class = import_module('whisper.transcribe').tqdm.tqdm
        # Real tqdm does not increment n when disabled.
        with bar_class(total=10, disable=verbose is None) as bar:
            bar.update(10)
        return {'text': 'ok'}

    model = MagicMock()
    model.transcribe.side_effect = run
    assert transcribe_audio(model, 'audio.wav', 'cpu', reported.append) == {'text': 'ok'}
    assert reported[-1] == 100
    assert module.tqdm.tqdm is tqdm


def test_progress_patch_restored_on_transcription_error(monkeypatch):
    from tqdm import tqdm

    module = types.ModuleType('whisper.transcribe')
    module.tqdm = types.SimpleNamespace(tqdm=tqdm)
    monkeypatch.setitem(sys.modules, 'whisper.transcribe', module)
    model = MagicMock()
    model.transcribe.side_effect = RuntimeError('failure')
    with pytest.raises(RuntimeError):
        transcribe_audio(model, 'audio.wav', 'cpu', lambda value: None)
    assert module.tqdm.tqdm is tqdm


def test_partial_subtitle_export_preserves_previous_file(tmp_path):
    from core.exporters import export_formats

    previous = tmp_path / 'audio.srt'
    previous.write_text('previous subtitles', encoding='utf-8')
    result = {'text': 'new text', 'segments': [
        {'start': 0, 'end': 1, 'text': 'valid'}, {'start': 1}
    ]}
    outputs = export_formats(str(tmp_path / 'audio.wav'), result, 'base', ['srt', 'txt'])
    assert outputs['srt'] is None
    assert outputs['txt'] is not None
    assert previous.read_text(encoding='utf-8') == 'previous subtitles'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['audio.srt', 'audio.txt']
