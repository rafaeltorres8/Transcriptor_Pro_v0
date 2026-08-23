from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QProgressBar, QPlainTextEdit, QVBoxLayout

_INDETERMINATE_FORMAT = "Cargando modelo…"
_DETERMINATE_FORMAT = "Transcribiendo… %p%"


class LogPanel(QGroupBox):
    """Panel de texto con el historial de progreso y una barra de progreso."""

    def __init__(self, parent=None) -> None:
        super().__init__("Progreso", parent)

        self.text_area = QPlainTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setMaximumBlockCount(500)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        self._set_indeterminate()

        layout = QVBoxLayout()
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.text_area)
        self.setLayout(layout)

    def append(self, message: str) -> None:
        """Añade una línea de texto al final del log."""
        self.text_area.appendPlainText(message)

    def clear(self) -> None:
        """Vacía el contenido del log."""
        self.text_area.clear()

    def set_busy(self, busy: bool) -> None:
        """Muestra u oculta la barra de progreso. Al activarse, siempre
        arranca en modo indeterminado (aún no hay porcentaje real)."""
        if busy:
            self._set_indeterminate()
        self.progress_bar.setVisible(busy)

    def set_progress_percent(self, percentage: float) -> None:
        """Actualiza la barra con el porcentaje real de avance (0-100).

        La primera llamada cambia la barra de modo indeterminado a
        determinado; las siguientes solo actualizan el valor.
        """
        if self.progress_bar.maximum() == 0:  # todavía en modo indeterminado
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setFormat(_DETERMINATE_FORMAT)
        clamped = max(0, min(100, round(percentage)))
        self.progress_bar.setValue(clamped)

    def _set_indeterminate(self) -> None:
        """Vuelve la barra a modo indeterminado (carga del modelo)."""
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat(_INDETERMINATE_FORMAT)
