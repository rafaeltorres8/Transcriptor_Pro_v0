import json
import os

import pytest

from core.exporters import (
    EXPORTERS,
    export_formats,
    export_json,
    export_md,
    export_srt,
    export_txt,
    export_vtt,
    format_timestamp_srt,
    format_timestamp_vtt,
)

SAMPLE_RESULT = {
    "text": "  Hola mundo. Esto es una prueba.  ",
    "language": "es",
    "segments": [
        {"id": 0, "start": 0.0, "end": 1.5, "text": " Hola mundo. "},
        {"id": 1, "start": 1.5, "end": 3.25, "text": " Esto es una prueba. "},
    ],
}


# --- format_timestamp ---

def test_format_timestamp_srt_basic():
    assert format_timestamp_srt(0) == "00:00:00,000"
    assert format_timestamp_srt(1.5) == "00:00:01,500"


def test_format_timestamp_srt_over_an_hour():
    # 1h 1m 1.001s
    seconds = 3661.001
    assert format_timestamp_srt(seconds) == "01:01:01,001"


def test_format_timestamp_srt_over_24_hours():
    # Regresión: el bug original con datetime.utcfromtimestamp fallaba pasadas 24h.
    seconds = 25 * 3600 + 30  # 25h 0m 30s
    assert format_timestamp_srt(seconds) == "25:00:30,000"


def test_format_timestamp_vtt_uses_dot_separator():
    assert format_timestamp_vtt(1.5) == "00:00:01.500"


# --- export_txt ---

def test_export_txt_writes_stripped_text(tmp_path):
    base = str(tmp_path / "audio")
    out_path = export_txt(base, SAMPLE_RESULT, "base")

    assert out_path == f"{base}.txt"
    content = open(out_path, encoding="utf-8").read()
    assert content == "Hola mundo. Esto es una prueba."


def test_export_txt_handles_missing_text_key(tmp_path):
    base = str(tmp_path / "audio")
    out_path = export_txt(base, {}, "base")
    assert open(out_path, encoding="utf-8").read() == ""


# --- export_md ---

def test_export_md_includes_header_and_model(tmp_path):
    base = str(tmp_path / "audio")
    out_path = export_md(base, SAMPLE_RESULT, "small")
    content = open(out_path, encoding="utf-8").read()

    assert "# Transcripción: audio" in content
    assert "`small`" in content
    assert "Hola mundo. Esto es una prueba." in content


# --- export_srt ---

def test_export_srt_format_and_numbering(tmp_path):
    base = str(tmp_path / "audio")
    out_path = export_srt(base, SAMPLE_RESULT, "base")
    content = open(out_path, encoding="utf-8").read()

    assert "1\n00:00:00,000 --> 00:00:01,500\nHola mundo." in content
    assert "2\n00:00:01,500 --> 00:00:03,250\nEsto es una prueba." in content


def test_export_srt_empty_segments(tmp_path):
    base = str(tmp_path / "audio")
    out_path = export_srt(base, {"text": "x", "segments": []}, "base")
    assert open(out_path, encoding="utf-8").read() == ""


# --- export_vtt ---

def test_export_vtt_has_header_and_dot_timestamps(tmp_path):
    base = str(tmp_path / "audio")
    out_path = export_vtt(base, SAMPLE_RESULT, "base")
    content = open(out_path, encoding="utf-8").read()

    assert content.startswith("WEBVTT\n\n")
    assert "00:00:00.000 --> 00:00:01.500" in content
    assert "Hola mundo." in content


# --- export_json ---

def test_export_json_structure(tmp_path):
    base = str(tmp_path / "audio")
    out_path = export_json(base, SAMPLE_RESULT, "medium")

    with open(out_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["model"] == "medium"
    assert data["language"] == "es"
    assert data["text"] == "Hola mundo. Esto es una prueba."
    assert len(data["segments"]) == 2
    assert data["segments"][0] == {
        "id": 0,
        "start": 0.0,
        "end": 1.5,
        "text": "Hola mundo.",
    }
    assert "generated_at" in data


# --- export_formats (orquestador) ---

def test_export_formats_writes_all_requested(tmp_path):
    audio_path = str(tmp_path / "audio.mp3")
    formats = ["txt", "md", "srt", "vtt", "json"]

    results = export_formats(audio_path, SAMPLE_RESULT, "base", formats)

    assert set(results.keys()) == set(formats)
    for fmt, path in results.items():
        assert path is not None
        assert os.path.exists(path)
        assert path.endswith(f".{fmt}")


def test_export_formats_respects_output_dir(tmp_path):
    audio_dir = tmp_path / "source"
    audio_dir.mkdir()
    audio_path = str(audio_dir / "audio.mp3")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    results = export_formats(
        audio_path, SAMPLE_RESULT, "base", ["txt"], output_dir=str(output_dir)
    )

    assert results["txt"] == str(output_dir / "audio.txt")
    assert os.path.exists(results["txt"])


def test_export_formats_unknown_format_reports_none(tmp_path):
    audio_path = str(tmp_path / "audio.mp3")
    results = export_formats(audio_path, SAMPLE_RESULT, "base", ["txt", "bogus"])

    assert results["txt"] is not None
    assert results["bogus"] is None


def test_export_formats_continues_after_failure(tmp_path, monkeypatch):
    audio_path = str(tmp_path / "audio.mp3")

    def broken_exporter(base_path, result, model_name):
        raise OSError("disk full")

    monkeypatch.setitem(EXPORTERS, "txt", broken_exporter)

    results = export_formats(audio_path, SAMPLE_RESULT, "base", ["txt", "md"])

    assert results["txt"] is None
    assert results["md"] is not None
    assert os.path.exists(results["md"])


def test_export_formats_empty_list_returns_empty_dict(tmp_path):
    audio_path = str(tmp_path / "audio.mp3")
    results = export_formats(audio_path, SAMPLE_RESULT, "base", [])
    assert results == {}
