from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QGroupBox, QHBoxLayout

from core.config import VALID_FORMATS

FORMAT_LABELS = {
    "txt": "TXT (texto plano)",
    "md": "Markdown",
    "srt": "SRT (subtítulos)",
    "vtt": "VTT (WebVTT)",
    "json": "JSON (estructurado)",
}

FORMAT_ORDER = ("txt", "md", "srt", "vtt", "json")


class FormatPanel(QGroupBox):
    """Checkboxes independientes, uno por formato de exportación soportado."""

    def __init__(self, default_formats: list[str] | None = None, parent=None) -> None:
        super().__init__("Formatos de salida", parent)

        defaults = set(default_formats or ("txt", "md", "srt"))
        self._checkboxes: dict[str, QCheckBox] = {}

        layout = QHBoxLayout()
        for fmt in FORMAT_ORDER:
            checkbox = QCheckBox(FORMAT_LABELS[fmt])
            checkbox.setChecked(fmt in defaults)
            self._checkboxes[fmt] = checkbox
            layout.addWidget(checkbox)

        self.setLayout(layout)

    def selected_formats(self) -> list[str]:
        """Devuelve la lista de formatos actualmente marcados."""
        return [fmt for fmt, box in self._checkboxes.items() if box.isChecked()]

    def set_selected_formats(self, formats: list[str]) -> None:
        """Marca únicamente los formatos indicados (ignora los inválidos)."""
        valid = set(formats) & VALID_FORMATS
        for fmt, box in self._checkboxes.items():
            box.setChecked(fmt in valid)
