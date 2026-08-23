from __future__ import annotations
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

APP_NAME = "TranscriptorPro"
CONFIG_FILENAME = "config.json"

DEFAULT_FORMATS = ("txt", "md", "srt")
VALID_FORMATS = frozenset({"txt", "md", "srt", "vtt", "json"})
VALID_MODELS = frozenset({"tiny", "base", "small", "medium", "large", "turbo"})


def get_config_dir() -> Path:
    """Devuelve el directorio de configuración específico de la plataforma.

    - Windows: %APPDATA%/TranscriptorPro
    - macOS/Linux: ~/.config/TranscriptorPro
    """
    if os.name == "nt":
        base = os.environ.get("APPDATA", str(Path.home()))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(base) / APP_NAME


def get_config_path() -> Path:
    """Devuelve la ruta completa del archivo de configuración."""
    return get_config_dir() / CONFIG_FILENAME


@dataclass
class AppConfig:
    """Ajustes persistentes de la aplicación."""

    ffmpeg_path: str = ""
    last_model: str = "base"
    output_formats: list[str] = field(default_factory=lambda: list(DEFAULT_FORMATS))
    last_output_dir: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convierte la configuración a un diccionario serializable a JSON."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        """Construye una instancia a partir de un diccionario, ignorando
        claves desconocidas y saneando valores inválidos."""
        known_fields = set(cls.__dataclass_fields__)
        filtered = {k: v for k, v in data.items() if k in known_fields}
        config = cls(**filtered)
        config._sanitize()
        return config

    def _sanitize(self) -> None:
        """Corrige valores inválidos con valores por defecto seguros."""
        if self.last_model not in VALID_MODELS:
            self.last_model = "base"
        cleaned_formats = [f for f in self.output_formats if f in VALID_FORMATS]
        self.output_formats = cleaned_formats or list(DEFAULT_FORMATS)


def load_config(path: Path | None = None) -> AppConfig:
    """Carga la configuración desde disco. Nunca lanza excepciones:
    ante cualquier error devuelve una configuración por defecto.
    """
    config_path = path or get_config_path()
    if not config_path.exists():
        return AppConfig()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return AppConfig.from_dict(data)
    except (json.JSONDecodeError, OSError, TypeError) as exc:
        logger.warning("Configuración corrupta o no legible en %s: %s", config_path, exc)
        return AppConfig()


def save_config(config: AppConfig, path: Path | None = None) -> bool:
    """Guarda la configuración en disco. Devuelve True si tuvo éxito."""
    config_path = path or get_config_path()
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
        return True
    except OSError as exc:
        logger.error("No se pudo guardar la configuración en %s: %s", config_path, exc)
        return False
