import subprocess

import pytest

from core.ffmpeg_utils import register_ffmpeg_path, resolve_ffmpeg_path
from core.ffmpeg_utils import test_ffmpeg_executable as check_ffmpeg_executable


def test_ffmpeg_executable_empty_path_returns_false():
    assert check_ffmpeg_executable("") is False


def test_ffmpeg_executable_nonexistent_path_returns_false():
    assert check_ffmpeg_executable("/path/does/not/exist/ffmpeg") is False


def test_ffmpeg_executable_valid_path(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: None)
    assert check_ffmpeg_executable("/usr/bin/ffmpeg") is True


def test_ffmpeg_executable_subprocess_error(monkeypatch):
    def raise_error(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "ffmpeg")

    monkeypatch.setattr(subprocess, "run", raise_error)
    assert check_ffmpeg_executable("/usr/bin/ffmpeg") is False


def test_ffmpeg_executable_timeout(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("ffmpeg", 10)

    monkeypatch.setattr(subprocess, "run", raise_timeout)
    assert check_ffmpeg_executable("/usr/bin/ffmpeg") is False


def test_resolve_ffmpeg_path_uses_valid_saved_path(monkeypatch, tmp_path):
    fake_ffmpeg = tmp_path / "ffmpeg"
    fake_ffmpeg.write_text("#!/bin/sh\necho fake")

    import core.ffmpeg_utils as mod

    monkeypatch.setattr(mod, "test_ffmpeg_executable", lambda p: p == str(fake_ffmpeg))

    result = resolve_ffmpeg_path(saved_path=str(fake_ffmpeg))
    assert result == str(fake_ffmpeg)


def test_resolve_ffmpeg_path_falls_back_to_system_path(monkeypatch, tmp_path):
    import core.ffmpeg_utils as mod

    executable = str(tmp_path / "ffmpeg")
    monkeypatch.setattr(mod.shutil, "which", lambda name: executable)
    monkeypatch.setattr(mod, "test_ffmpeg_executable", lambda p: p == executable)

    result = resolve_ffmpeg_path(saved_path="")
    assert result == executable


def test_resolve_ffmpeg_path_returns_empty_when_nothing_found(monkeypatch):
    import core.ffmpeg_utils as mod

    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    monkeypatch.setattr(mod, "test_ffmpeg_executable", lambda p: False)

    result = resolve_ffmpeg_path(saved_path="/bad/path")
    assert result == ""


def test_register_ffmpeg_path_invalid_returns_false(monkeypatch):
    import core.ffmpeg_utils as mod

    monkeypatch.setattr(mod, "test_ffmpeg_executable", lambda p: False)
    assert register_ffmpeg_path("/bad/path") is False


def test_register_ffmpeg_path_system_ffmpeg_does_not_touch_path(monkeypatch):
    import core.ffmpeg_utils as mod

    monkeypatch.setattr(mod, "test_ffmpeg_executable", lambda p: True)
    original_path = mod.os.environ.get("PATH", "")

    assert register_ffmpeg_path("ffmpeg") is True
    assert mod.os.environ.get("PATH", "") == original_path


def test_register_ffmpeg_path_custom_path_prepends_to_path(monkeypatch, tmp_path):
    import core.ffmpeg_utils as mod

    fake_ffmpeg = tmp_path / "ffmpeg"
    fake_ffmpeg.write_text("#!/bin/sh\necho fake")

    monkeypatch.setattr(mod, "test_ffmpeg_executable", lambda p: True)
    monkeypatch.setenv("PATH", "/usr/bin")

    assert register_ffmpeg_path(str(fake_ffmpeg)) is True
    assert str(tmp_path) in mod.os.environ["PATH"].split(mod.os.pathsep)


def test_resolve_ffmpeg_path_normalizes_saved_relative_path(monkeypatch, tmp_path):
    import core.ffmpeg_utils as mod

    executable = tmp_path / "ffmpeg"
    executable.write_text("placeholder")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod, "test_ffmpeg_executable", lambda path: True)

    assert resolve_ffmpeg_path("ffmpeg") == str(executable.resolve())


def test_selected_ffmpeg_directory_takes_priority_when_already_in_path(monkeypatch, tmp_path):
    import core.ffmpeg_utils as mod

    folder = str(tmp_path)
    monkeypatch.setattr(mod, "test_ffmpeg_executable", lambda path: True)
    monkeypatch.setenv("PATH", mod.os.pathsep.join(["other", folder]))
    assert register_ffmpeg_path(str(tmp_path / "ffmpeg"))
    assert mod.os.environ["PATH"].split(mod.os.pathsep) == [folder, "other"]
