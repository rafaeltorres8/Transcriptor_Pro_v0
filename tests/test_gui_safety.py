import os
from unittest.mock import MagicMock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMessageBox

from core.config import AppConfig
from gui.main_window import MainWindow
from gui.widgets.ffmpeg_panel import FFmpegPanel


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, monkeypatch):
    import gui.main_window as main
    import gui.widgets.ffmpeg_panel as ffmpeg

    monkeypatch.setattr(main, 'load_config', lambda: AppConfig())
    monkeypatch.setattr(main, 'save_config', lambda config: True)
    monkeypatch.setattr(ffmpeg, 'resolve_ffmpeg_path', lambda path: '')
    view = MainWindow()
    yield view
    view.worker = None
    view.close()


def test_close_is_rejected_while_worker_is_running(window, monkeypatch):
    monkeypatch.setattr(QMessageBox, 'information', lambda *a: None)
    window.worker = MagicMock()
    window.worker.isRunning.return_value = True
    event = QCloseEvent()
    window.closeEvent(event)
    assert not event.isAccepted()
    window.worker.isRunning.return_value = False
    window.closeEvent(event)
    assert event.isAccepted()


def test_directory_is_not_a_media_file(window, tmp_path):
    window.file_panel.set_file(str(tmp_path))
    assert not window.file_panel.is_valid()


def test_failed_ffmpeg_registration_is_not_ready(app, monkeypatch):
    import gui.widgets.ffmpeg_panel as panel

    monkeypatch.setattr(panel, 'resolve_ffmpeg_path', lambda path: '')
    monkeypatch.setattr(panel, 'register_ffmpeg_path', lambda path: False)
    view = FFmpegPanel()
    view._set_ready('missing.exe')
    assert not view.is_ready()


def test_overwrite_declined_does_not_start_worker(window, tmp_path, monkeypatch):
    audio = tmp_path / 'audio.wav'
    audio.write_bytes(b'placeholder')
    (tmp_path / 'audio.txt').write_text('existing')
    window.file_panel.set_file(str(audio))
    window.ffmpeg_panel._current_path = 'ffmpeg'
    monkeypatch.setattr(QMessageBox, 'question', lambda *a: QMessageBox.StandardButton.No)
    window._on_transcribe_clicked()
    assert window.worker is None
    assert (tmp_path / 'audio.txt').read_text() == 'existing'


def test_missing_output_directory_does_not_start_worker(window, tmp_path, monkeypatch):
    audio = tmp_path / 'audio.wav'
    audio.write_bytes(b'placeholder')
    window.file_panel.set_file(str(audio))
    window.file_panel.output_dir_edit.setText(str(tmp_path / 'missing'))
    window.ffmpeg_panel._current_path = 'ffmpeg'
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: None)
    window._on_transcribe_clicked()
    assert window.worker is None


def test_worker_reports_failure_when_all_exports_fail(app, monkeypatch):
    from gui.worker import TranscriptionWorker
    from core import exporters, transcriber

    monkeypatch.setattr(transcriber, 'detect_device', lambda: 'cpu')
    monkeypatch.setattr(transcriber, 'load_model', lambda *a, **k: object())
    monkeypatch.setattr(transcriber, 'transcribe_audio', lambda *a, **k: {'text': 'ok'})
    monkeypatch.setattr(exporters, 'export_formats', lambda *a, **k: {'txt': None})
    worker = TranscriptionWorker('audio.wav', 'base', ['txt'])
    failures, successes = [], []
    worker.failed.connect(failures.append)
    worker.finished_ok.connect(lambda *args: successes.append(args))
    worker.run()
    assert failures and not successes
