
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from core.ffmpeg_utils import register_ffmpeg_path, resolve_ffmpeg_path, test_ffmpeg_executable


class FFmpegPanel(QGroupBox):
    """Grupo visual con el estado de FFmpeg y un botón para seleccionarlo."""

    ffmpeg_ready = Signal(str)  # emite la ruta válida cuando FFmpeg está listo

    def __init__(self, saved_path: str = "", parent=None) -> None:
        super().__init__("FFmpeg", parent)
        self._current_path = ""

        self.status_label = QLabel("Comprobando FFmpeg...")
        self.select_button = QPushButton("Seleccionar ejecutable…")
        self.select_button.clicked.connect(self._on_select_clicked)

        row = QHBoxLayout()
        row.addWidget(self.status_label, stretch=1)
        row.addWidget(self.select_button)

        layout = QVBoxLayout()
        layout.addLayout(row)
        self.setLayout(layout)

        self.try_autodetect(saved_path)

    def try_autodetect(self, saved_path: str = "") -> None:
        """Intenta resolver FFmpeg automáticamente (config guardada o PATH)."""
        resolved = resolve_ffmpeg_path(saved_path)
        if resolved:
            self._set_ready(resolved)
        else:
            self._set_not_ready("No se encontró FFmpeg automáticamente.")

    def _on_select_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecciona el ejecutable de FFmpeg",
            "",
            "Ejecutable FFmpeg (ffmpeg ffmpeg.exe);;Todos los archivos (*)",
        )
        if not path:
            return

        if test_ffmpeg_executable(path) and register_ffmpeg_path(path):
            self._set_ready(path)
        else:
            self._set_not_ready(f"El archivo seleccionado no es un FFmpeg válido: {path}")

    def _set_ready(self, path: str) -> None:
        register_ffmpeg_path(path)
        self._current_path = path
        display = "sistema (PATH)" if path == "ffmpeg" else path
        self.status_label.setText(f"✔️ FFmpeg listo: {display}")
        self.status_label.setStyleSheet("color: #2e7d32; font-weight: 600;")
        self.ffmpeg_ready.emit(path)

    def _set_not_ready(self, message: str) -> None:
        self._current_path = ""
        self.status_label.setText(f"❌ {message}")
        self.status_label.setStyleSheet("color: #c62828; font-weight: 600;")

    def current_path(self) -> str:
        """Devuelve la ruta de FFmpeg actualmente validada (vacía si no hay)."""
        return self._current_path

    def is_ready(self) -> bool:
        """True si hay una ruta de FFmpeg válida y registrada."""
        return bool(self._current_path)
