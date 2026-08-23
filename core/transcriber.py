from __future__ import annotations
import logging
from contextlib import contextmanager
from typing import Any, Iterator, Protocol

logger = logging.getLogger(__name__)

VALID_MODELS = ("tiny", "base", "small", "medium", "large", "turbo")


class ProgressCallback(Protocol):
    """Firma de un callback opcional para reportar progreso textual."""

    def __call__(self, message: str) -> None: ...


class ProgressPercentCallback(Protocol):
    """Firma de un callback opcional para reportar progreso real (0-100)."""

    def __call__(self, percentage: float) -> None: ...


def detect_device() -> str:
    """Devuelve 'cuda' si hay una GPU NVIDIA disponible, si no 'cpu'."""
    try:
        import torch
    except ImportError:
        logger.warning("PyTorch no está instalado; se usará CPU por defecto.")
        return "cpu"

    return "cuda" if torch.cuda.is_available() else "cpu"


def load_model(model_name: str, device: str) -> Any:
    """Carga un modelo Whisper. Lanza ValueError si `model_name` no es válido,
    o RuntimeError si la carga falla."""
    if model_name not in VALID_MODELS:
        raise ValueError(f"Modelo '{model_name}' no válido. Opciones: {', '.join(VALID_MODELS)}")

    try:
        import whisper
    except ImportError as exc:
        raise RuntimeError(
            "El paquete 'openai-whisper' no está instalado. "
            "Instálalo con: pip install openai-whisper"
        ) from exc

    try:
        return whisper.load_model(model_name, device=device)
    except Exception as exc:  # whisper puede lanzar varios tipos de error
        raise RuntimeError(f"Error al cargar el modelo Whisper '{model_name}': {exc}") from exc


def _make_progress_tqdm(base_tqdm_cls: type, callback: ProgressPercentCallback) -> type:
    """Crea una subclase de `base_tqdm_cls` que reenvía el avance (0-100) a
    `callback`.

    Internamente, `whisper.transcribe()` reporta su progreso mediante una
    barra `tqdm` sobre los frames de audio ya procesados (sin exponer un
    callback propio). Heredando de la clase `tqdm` original que ya usa
    `whisper.transcribe` (en vez de volver a importar el paquete `tqdm`
    por separado) interceptamos cada `update()` sin tocar el código
    interno de la librería.
    """

    class _CallbackProgressBar(base_tqdm_cls):  # type: ignore[misc]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self._reported = self.n

        def update(self, n: float = 1) -> Any:
            """Delega en `tqdm.update` y, con cada avance, reenvía el
            porcentaje acumulado (0-100) a `callback`."""
            result = super().update(n)
            self._reported += n
            if self.total:
                percentage = max(0.0, min(100.0, (self._reported / self.total) * 100))
                try:
                    callback(percentage)
                except Exception:  # pylint: disable=broad-exception-caught
                    # El callback lo define quien llama (p. ej. la GUI); un
                    # fallo ahí no debe interrumpir la transcripción en curso.
                    logger.debug("Error en el callback de progreso.", exc_info=True)
            return result

    return _CallbackProgressBar


@contextmanager
def _progress_reporting(callback: ProgressPercentCallback | None) -> Iterator[None]:
    """Si se da un `callback`, parchea temporalmente la barra de progreso
    interna de `whisper.transcribe` para reportar el porcentaje real de
    avance; restaura la clase original al salir, incluso si algo falla.

    Si `whisper` no está instalado (p. ej. en tests ligeros) se hace un
    no-op silencioso: la transcripción sigue funcionando, simplemente sin
    progreso detallado.
    """
    if callback is None:
        yield
        return

    try:
        import whisper.transcribe as whisper_transcribe_module
    except ImportError:
        logger.debug("whisper.transcribe no disponible; sin progreso detallado.")
        yield
        return

    original_tqdm = whisper_transcribe_module.tqdm.tqdm
    whisper_transcribe_module.tqdm.tqdm = _make_progress_tqdm(original_tqdm, callback)
    try:
        yield
    finally:
        whisper_transcribe_module.tqdm.tqdm = original_tqdm


def transcribe_audio(
    model: Any,
    audio_path: str,
    device: str,
    progress_callback: ProgressPercentCallback | None = None,
) -> dict[str, Any]:
    """Ejecuta la transcripción y devuelve el resultado crudo de Whisper.

    Si se proporciona `progress_callback`, se invoca repetidamente durante
    la transcripción con el porcentaje de avance real (0.0-100.0).
    """
    use_fp16 = device == "cuda"
    with _progress_reporting(progress_callback):
        return model.transcribe(audio_path, fp16=use_fp16)
