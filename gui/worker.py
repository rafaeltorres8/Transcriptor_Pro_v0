from __future__ import annotations
from typing import Any
from PySide6.QtCore import QThread, Signal
from core import exporters, transcriber

class TranscriptionWorker(QThread):
    """Ejecuta: carga de modelo -> transcripción -> exportación de formatos.

    Señales:
        progress(str): mensajes de estado para mostrar en el log de la UI.
        progress_percent(float): porcentaje real de avance (0-100) durante
            la transcripción, emitido por Whisper frame a frame.
        finished_ok(str, dict): ruta del audio procesado y {formato: ruta|None}.
        failed(str): mensaje de error si algo falla.
    """

    progress = Signal(str)
    progress_percent = Signal(float)
    finished_ok = Signal(str, dict)
    failed = Signal(str)

    def __init__(
        self,
        audio_path: str,
        model_name: str,
        output_formats: list[str],
        output_dir: str = "",
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.audio_path = audio_path
        self.model_name = model_name
        self.output_formats = output_formats
        self.output_dir = output_dir

    def run(self) -> None:
        """Punto de entrada del hilo: ejecuta el pipeline completo y emite
        señales de progreso, éxito o fallo hacia el hilo principal (UI)."""
        try:
            device = transcriber.detect_device()
            self.progress.emit(f"🚀 Procesando usando hardware: {device.upper()}")

            self.progress.emit(f"📥 Cargando modelo '{self.model_name}'...")
            model = transcriber.load_model(self.model_name, device=device)
            self.progress.emit("✔️ Modelo cargado con éxito.")

            self.progress.emit(f"⏳ Transcribiendo: {self.audio_path}")
            result = transcriber.transcribe_audio(
                model,
                self.audio_path,
                device=device,
                progress_callback=self._emit_progress_percent,
            )

            self.progress.emit("💾 Exportando formatos seleccionados...")
            export_results = exporters.export_formats(
                self.audio_path,
                result,
                self.model_name,
                self.output_formats,
                output_dir=self.output_dir,
            )

            self.finished_ok.emit(self.audio_path, export_results)
        except (ValueError, RuntimeError, OSError) as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Salvaguarda intencional: este hilo no debe morir en silencio
            # ante un error no anticipado (p. ej. un bug interno de whisper);
            # se reporta a la UI en vez de crashear la aplicación.
            self.failed.emit(f"Error inesperado: {exc}")

    def _emit_progress_percent(self, percentage: float) -> None:
        """Reenvía el porcentaje de avance como señal Qt.

        Existe como método propio (en vez de pasar `progress_percent.emit`
        directamente) porque el `emit` genérico de PySide6 no expone una
        firma tipada compatible con `ProgressPercentCallback` para mypy.
        """
        self.progress_percent.emit(percentage)
