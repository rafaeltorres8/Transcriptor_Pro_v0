from __future__ import annotations
import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

FFMPEG_TIMEOUT_SECONDS = 10


def test_ffmpeg_executable(path: str) -> bool:
    """Comprueba que el ejecutable termina con éxito al recibir `-version`.

    Esta prueba ejecuta el archivo; no acredita su identidad ni su procedencia.
    Solo deben usarse ejecutables de confianza.
    """
    if not path:
        return False
    try:
        subprocess.run(
            [path, "-version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=FFMPEG_TIMEOUT_SECONDS,
        )
        return True
    except (subprocess.SubprocessError, OSError):
        return False


def resolve_ffmpeg_path(saved_path: str = "") -> str:
    """Intenta resolver una ruta de FFmpeg utilizable sin pedir intervención
    del usuario. Devuelve cadena vacía si no se encuentra ninguna.
    """
    if saved_path and os.path.exists(saved_path) and test_ffmpeg_executable(saved_path):
        return str(Path(saved_path).resolve())

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg and test_ffmpeg_executable(system_ffmpeg):
        return str(Path(system_ffmpeg).resolve())

    return ""


def register_ffmpeg_path(path: str) -> bool:
    """Valida `path` y, si es un ejecutable de FFmpeg funcional, lo añade
    temporalmente al PATH del proceso actual (para que Whisper lo use).
    Devuelve True si el registro tuvo éxito.
    """
    if not test_ffmpeg_executable(path):
        return False

    if path != "ffmpeg":
        folder = str(Path(path).resolve().parent)
        current_path = os.environ.get("PATH", "")
        if folder not in current_path.split(os.pathsep):
            os.environ["PATH"] = folder + os.pathsep + current_path

    return True
