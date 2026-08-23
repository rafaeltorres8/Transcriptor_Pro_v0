from __future__ import annotations

import os

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)

_MEDIA_EXTENSIONS = "*.mp3 *.wav *.m4a *.flac *.mp4 *.mkv *.aac"
MEDIA_FILTER = f"Archivos multimedia ({_MEDIA_EXTENSIONS});;Todos los archivos (*)"


class FilePanel(QGroupBox):
    """Permite elegir el archivo a transcribir y, opcionalmente, la carpeta
    donde guardar los resultados (por defecto, la misma del archivo)."""

    file_selected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__("Archivo", parent)

        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("Ningún archivo seleccionado…")
        self.file_edit.setReadOnly(True)
        browse_file_btn = QPushButton("Examinar…")
        browse_file_btn.clicked.connect(self._on_browse_file)

        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Misma carpeta que el archivo de origen")
        browse_dir_btn = QPushButton("Elegir carpeta…")
        browse_dir_btn.clicked.connect(self._on_browse_output_dir)

        layout = QGridLayout()
        layout.addWidget(QLabel("Audio/Video:"), 0, 0)
        layout.addWidget(self.file_edit, 0, 1)
        layout.addWidget(browse_file_btn, 0, 2)

        layout.addWidget(QLabel("Carpeta de salida:"), 1, 0)
        layout.addWidget(self.output_dir_edit, 1, 1)
        layout.addWidget(browse_dir_btn, 1, 2)

        layout.setColumnStretch(1, 1)
        self.setLayout(layout)

    def _on_browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecciona archivo de audio o video", "", MEDIA_FILTER
        )
        if path:
            self.file_edit.setText(path)
            self.file_selected.emit(path)

    def _on_browse_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Selecciona carpeta de salida")
        if directory:
            self.output_dir_edit.setText(directory)

    def selected_file(self) -> str:
        """Devuelve la ruta del archivo de audio/video seleccionado."""
        return self.file_edit.text().strip()

    def selected_output_dir(self) -> str:
        """Devuelve la carpeta de salida elegida (vacía si no se especificó)."""
        return self.output_dir_edit.text().strip()

    def set_file(self, path: str) -> None:
        """Establece programáticamente la ruta del archivo (usado en tests)."""
        self.file_edit.setText(path)

    def is_valid(self) -> bool:
        """True si hay una ruta de archivo no vacía y existente en disco."""
        path = self.selected_file()
        return bool(path) and os.path.exists(path)
