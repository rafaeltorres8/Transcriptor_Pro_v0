from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.config import AppConfig, load_config, save_config
from gui.widgets.ffmpeg_panel import FFmpegPanel
from gui.widgets.file_panel import FilePanel
from gui.widgets.format_panel import FormatPanel
from gui.widgets.hardware_panel import HardwarePanel
from gui.widgets.log_panel import LogPanel
from gui.widgets.model_panel import ModelPanel
from gui.worker import TranscriptionWorker

WINDOW_TITLE = "Transcriptor Pro — Whisper + FFmpeg"


class MainWindow(QMainWindow):
    """Ventana principal: conecta los paneles de configuración con el
    worker de transcripción en segundo plano."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(720, 640)

        self.config: AppConfig = load_config()
        self.worker: TranscriptionWorker | None = None

        self.ffmpeg_panel = FFmpegPanel(saved_path=self.config.ffmpeg_path)
        self.file_panel = FilePanel()
        self.hardware_panel = HardwarePanel()
        self.model_panel = ModelPanel(default_model=self.config.last_model)
        self.format_panel = FormatPanel(default_formats=self.config.output_formats)
        self.log_panel = LogPanel()

        self.transcribe_button = QPushButton("Transcribir")
        self.transcribe_button.setMinimumHeight(40)
        self.transcribe_button.clicked.connect(self._on_transcribe_clicked)

        self.ffmpeg_panel.ffmpeg_ready.connect(self._on_ffmpeg_ready)
        self.hardware_panel.model_recommended.connect(self.model_panel.set_selected_model)

        central = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.ffmpeg_panel)
        layout.addWidget(self.file_panel)
        layout.addWidget(self.hardware_panel)
        layout.addWidget(self.model_panel)
        layout.addWidget(self.format_panel)
        layout.addWidget(self.transcribe_button)
        layout.addWidget(self.log_panel, stretch=1)
        central.setLayout(layout)
        self.setCentralWidget(central)

        if self.config.last_output_dir:
            self.file_panel.output_dir_edit.setText(self.config.last_output_dir)

    def _on_ffmpeg_ready(self, path: str) -> None:
        """Persiste la ruta de FFmpeg validada en la configuración."""
        self.config.ffmpeg_path = path
        save_config(self.config)

    def _on_transcribe_clicked(self) -> None:
        """Valida las precondiciones y lanza el worker de transcripción."""
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(self, "Procesando", "Ya hay una transcripción en curso.")
            return

        if not self.ffmpeg_panel.is_ready():
            QMessageBox.warning(
                self,
                "FFmpeg no configurado",
                "Debes seleccionar un ejecutable de FFmpeg válido antes de continuar.",
            )
            return

        if not self.file_panel.is_valid():
            QMessageBox.warning(
                self,
                "Archivo no válido",
                "Selecciona un archivo de audio o video existente.",
            )
            return

        formats = self.format_panel.selected_formats()
        if not formats:
            QMessageBox.warning(
                self,
                "Sin formatos seleccionados",
                "Selecciona al menos un formato de salida.",
            )
            return

        audio_path = self.file_panel.selected_file()
        model_name = self.model_panel.selected_model()
        output_dir = self.file_panel.selected_output_dir()

        self._persist_preferences(model_name, formats, output_dir)

        self.log_panel.clear()
        self.log_panel.set_busy(True)
        self.transcribe_button.setEnabled(False)
        self.transcribe_button.setText("Procesando…")

        self.worker = TranscriptionWorker(
            audio_path=audio_path,
            model_name=model_name,
            output_formats=formats,
            output_dir=output_dir,
        )
        self.worker.progress.connect(self.log_panel.append)
        self.worker.progress_percent.connect(self.log_panel.set_progress_percent)
        self.worker.finished_ok.connect(self._on_finished_ok)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _persist_preferences(self, model_name: str, formats: list[str], output_dir: str) -> None:
        """Guarda en disco las últimas preferencias usadas por el usuario."""
        self.config.last_model = model_name
        self.config.output_formats = formats
        self.config.last_output_dir = output_dir
        save_config(self.config)

    def _on_finished_ok(self, audio_path: str, export_results: dict[str, str | None]) -> None:
        """Informa en el log qué formatos se generaron correctamente."""
        successful = [fmt for fmt, path in export_results.items() if path]
        failed = [fmt for fmt, path in export_results.items() if not path]

        file_name = os.path.basename(audio_path)
        self.log_panel.append(f"✅ ¡Completado! '{file_name}' -> {', '.join(successful)}")
        if failed:
            self.log_panel.append(f"⚠️ No se pudieron generar: {', '.join(failed)}")

        self._reset_ui_after_run()

    def _on_failed(self, message: str) -> None:
        """Muestra el error tanto en el log como en un diálogo modal."""
        self.log_panel.append(f"❌ Error: {message}")
        QMessageBox.critical(self, "Error durante la transcripción", message)
        self._reset_ui_after_run()

    def _reset_ui_after_run(self) -> None:
        """Restaura el botón y la barra de progreso a su estado inicial."""
        self.log_panel.set_busy(False)
        self.transcribe_button.setEnabled(True)
        self.transcribe_button.setText("Transcribir")
