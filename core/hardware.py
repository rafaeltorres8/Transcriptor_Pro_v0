from __future__ import annotations
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Requisitos de VRAM tal como los publica el README oficial de openai/whisper
# (https://github.com/openai/whisper#available-models-and-languages).
WHISPER_VRAM_GB: dict[str, float] = {
    "tiny": 1.0,
    "base": 1.0,
    "small": 2.0,
    "medium": 5.0,
    "turbo": 6.0,
    "large": 10.0,
}

# No existe una tabla oficial de RAM equivalente a la de VRAM para
# inferencia en CPU. Como estimación práctica se aplica un factor de
# seguridad sobre la cifra oficial de VRAM (la inferencia en CPU suele
# necesitar más memoria que su equivalente en GPU) más un margen fijo
# para el propio proceso de Python y el sistema operativo.
_CPU_RAM_SAFETY_FACTOR = 2.0
_CPU_RAM_OVERHEAD_GB = 2.0

# Modelos ordenados de menor a mayor exigencia de recursos.
MODEL_ORDER: tuple[str, ...] = ("tiny", "base", "small", "medium", "turbo", "large")

_DEFAULT_MODEL = "tiny"


@dataclass(frozen=True)
class HardwareInfo:
    """Instantánea del hardware detectado en la máquina actual."""

    total_ram_gb: float
    ram_detected: bool
    gpu_available: bool
    total_vram_gb: float | None
    gpu_name: str | None


@dataclass(frozen=True)
class ModelRecommendation:
    """Resultado de recomendar un modelo Whisper según el hardware."""

    model_name: str
    reason: str
    hardware: HardwareInfo


def detect_ram_gb() -> tuple[float, bool]:
    """Devuelve (RAM total del sistema en GB, si se pudo detectar).

    Nunca lanza: si `psutil` no está instalado o falla la consulta,
    devuelve (0.0, False) en vez de interrumpir la detección de hardware.
    """
    try:
        import psutil
    except ImportError:
        logger.warning("psutil no está instalado; no se puede detectar la RAM.")
        return 0.0, False

    try:
        return psutil.virtual_memory().total / (1024**3), True
    except Exception:  # pylint: disable=broad-exception-caught
        # Defensivo: la detección de hardware no debe romper la app por un
        # fallo inesperado de psutil en alguna plataforma concreta.
        logger.warning("No se pudo leer la RAM del sistema.", exc_info=True)
        return 0.0, False


def detect_vram_gb() -> tuple[float | None, str | None]:
    """Devuelve (VRAM total en GB, nombre) de la GPU principal (índice 0),
    o (None, None) si no hay ninguna GPU CUDA disponible."""
    try:
        import torch
    except ImportError:
        return None, None

    try:
        if not torch.cuda.is_available():
            return None, None
        props = torch.cuda.get_device_properties(0)
        return props.total_memory / (1024**3), props.name
    except Exception:  # pylint: disable=broad-exception-caught
        # Defensivo: la detección de hardware no debe romper la app por un
        # fallo inesperado de CUDA/torch en alguna configuración concreta.
        logger.warning("No se pudo consultar la VRAM de la GPU.", exc_info=True)
        return None, None


def detect_hardware() -> HardwareInfo:
    """Detecta la RAM total del sistema y, si existe, la VRAM de la GPU
    principal."""
    total_ram, ram_detected = detect_ram_gb()
    total_vram, gpu_name = detect_vram_gb()
    return HardwareInfo(
        total_ram_gb=total_ram,
        ram_detected=ram_detected,
        gpu_available=total_vram is not None,
        total_vram_gb=total_vram,
        gpu_name=gpu_name,
    )


def _best_model_for_budget(budget_gb: float, requirements: dict[str, float]) -> str:
    """Devuelve, de `MODEL_ORDER`, el modelo más exigente cuyo requisito
    entra dentro de `budget_gb`. Si ninguno entra, devuelve el más ligero."""
    best = _DEFAULT_MODEL
    for model_name in MODEL_ORDER:
        if requirements[model_name] <= budget_gb:
            best = model_name
    return best


def recommend_model(hardware: HardwareInfo | None = None) -> ModelRecommendation:
    """Recomienda un modelo Whisper según el hardware detectado.

    Si hay GPU disponible, la recomendación se basa en la VRAM (factor
    limitante real para Whisper) usando los requisitos oficiales del
    proyecto. Si no hay GPU, se basa en la RAM del sistema con un margen
    de seguridad, ya que ejecutar Whisper en CPU consume más memoria que
    su equivalente en VRAM.
    """
    hw = hardware or detect_hardware()

    if hw.gpu_available and hw.total_vram_gb is not None:
        model = _best_model_for_budget(hw.total_vram_gb, WHISPER_VRAM_GB)
        reason = (
            f"GPU detectada ({hw.gpu_name}, {hw.total_vram_gb:.1f} GB VRAM); "
            "recomendación basada en los requisitos oficiales de VRAM de Whisper."
        )
        return ModelRecommendation(model_name=model, reason=reason, hardware=hw)

    if not hw.ram_detected:
        reason = (
            "No se pudo detectar la RAM del sistema (falta 'psutil'); "
            f"se recomienda '{_DEFAULT_MODEL}' de forma conservadora."
        )
        return ModelRecommendation(model_name=_DEFAULT_MODEL, reason=reason, hardware=hw)

    cpu_requirements = {
        name: vram_gb * _CPU_RAM_SAFETY_FACTOR + _CPU_RAM_OVERHEAD_GB
        for name, vram_gb in WHISPER_VRAM_GB.items()
    }
    model = _best_model_for_budget(hw.total_ram_gb, cpu_requirements)
    reason = (
        f"No se detectó GPU compatible; recomendación basada en la RAM del "
        f"sistema ({hw.total_ram_gb:.1f} GB) con margen para el sistema "
        "operativo (estimación orientativa, no existe una tabla oficial de "
        "RAM para CPU)."
    )
    return ModelRecommendation(model_name=model, reason=reason, hardware=hw)
