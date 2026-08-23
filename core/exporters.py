from __future__ import annotations
import json
import logging
import os
from datetime import datetime
from typing import Any, Callable

logger = logging.getLogger(__name__)

TranscriptionResult = dict[str, Any]


def format_timestamp_srt(seconds: float) -> str:
    """Convierte segundos a formato SRT `HH:MM:SS,mmm` (sin límite de 24h)."""
    total_ms = int(round(seconds * 1000))
    hrs, remainder = divmod(total_ms, 3_600_000)
    mins, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def format_timestamp_vtt(seconds: float) -> str:
    """Convierte segundos a formato WebVTT `HH:MM:SS.mmm`."""
    return format_timestamp_srt(seconds).replace(",", ".")


def export_txt(base_path: str, result: TranscriptionResult, model_name: str) -> str:
    """Exporta el texto plano de la transcripción a un archivo .txt.

    `model_name` no se usa en este formato, pero se mantiene en la firma
    para que todos los exportadores compartan la misma interfaz uniforme
    y puedan intercambiarse en `EXPORTERS`.
    """
    del model_name  # no aplica a este formato; ver docstring
    out_path = f"{base_path}.txt"
    text = result.get("text", "").strip()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return out_path


def export_md(base_path: str, result: TranscriptionResult, model_name: str) -> str:
    """Exporta la transcripción a Markdown con una cabecera de metadatos
    (nombre de archivo, modelo usado y fecha de generación)."""
    out_path = f"{base_path}.md"
    text = result.get("text", "").strip()
    source_name = os.path.basename(base_path)
    header = (
        f"# Transcripción: {source_name}\n\n"
        f"- **Modelo:** `{model_name}` | "
        f"**Fecha:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n---\n\n"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header + text)
    return out_path


def export_srt(base_path: str, result: TranscriptionResult, model_name: str) -> str:
    """Exporta subtítulos en formato SRT con marcas de tiempo por segmento."""
    del model_name  # no aplica a este formato
    out_path = f"{base_path}.srt"
    segments = result.get("segments", [])
    with open(out_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, start=1):
            start = format_timestamp_srt(segment["start"])
            end = format_timestamp_srt(segment["end"])
            text = segment["text"].strip()
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
    return out_path


def export_vtt(base_path: str, result: TranscriptionResult, model_name: str) -> str:
    """Exporta subtítulos en formato WebVTT con marcas de tiempo por segmento."""
    del model_name  # no aplica a este formato
    out_path = f"{base_path}.vtt"
    segments = result.get("segments", [])
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for segment in segments:
            start = format_timestamp_vtt(segment["start"])
            end = format_timestamp_vtt(segment["end"])
            text = segment["text"].strip()
            f.write(f"{start} --> {end}\n{text}\n\n")
    return out_path


def export_json(base_path: str, result: TranscriptionResult, model_name: str) -> str:
    """Exporta la transcripción completa (texto, idioma y segmentos) como JSON
    estructurado, incluyendo metadatos de generación."""
    out_path = f"{base_path}.json"
    payload = {
        "model": model_name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "text": result.get("text", "").strip(),
        "language": result.get("language"),
        "segments": [
            {
                "id": seg.get("id"),
                "start": seg.get("start"),
                "end": seg.get("end"),
                "text": seg.get("text", "").strip(),
            }
            for seg in result.get("segments", [])
        ],
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return out_path


EXPORTERS: dict[str, Callable[[str, TranscriptionResult, str], str]] = {
    "txt": export_txt,
    "md": export_md,
    "srt": export_srt,
    "vtt": export_vtt,
    "json": export_json,
}


def export_formats(
    audio_path: str,
    result: TranscriptionResult,
    model_name: str,
    formats: list[str],
    output_dir: str = "",
) -> dict[str, str | None]:
    """Exporta `result` en cada uno de los `formats` solicitados.

    Devuelve un diccionario {formato: ruta_generada} para los que tuvieron
    éxito, y {formato: None} para los que fallaron (se registra el error
    pero no se interrumpe la exportación de los demás formatos).
    """
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    target_dir = output_dir or os.path.dirname(os.path.abspath(audio_path))
    base_path = os.path.join(target_dir, base_name)

    results: dict[str, str | None] = {}
    for fmt in formats:
        exporter = EXPORTERS.get(fmt)
        if exporter is None:
            logger.warning("Formato de exportación desconocido: %s", fmt)
            results[fmt] = None
            continue
        try:
            results[fmt] = exporter(base_path, result, model_name)
        except (OSError, KeyError) as exc:
            logger.error("Error exportando formato '%s': %s", fmt, exc)
            results[fmt] = None

    return results
