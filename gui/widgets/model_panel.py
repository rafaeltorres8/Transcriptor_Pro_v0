
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QGroupBox, QHBoxLayout, QLabel

from core.transcriber import VALID_MODELS

MODEL_DESCRIPTIONS = {
    "tiny": "tiny — más rápido, menor precisión",
    "base": "base — equilibrio recomendado",
    "small": "small — buena precisión",
    "medium": "medium — alta precisión, más lento",
    "large": "large — máxima precisión, requiere más recursos",
    "turbo": "turbo — rápido y preciso (si está disponible)",
}


class ModelPanel(QGroupBox):
    """Combo box con los modelos Whisper disponibles."""

    def __init__(self, default_model: str = "base", parent=None) -> None:
        super().__init__("Modelo Whisper", parent)

        self.combo = QComboBox()
        for model_name in VALID_MODELS:
            self.combo.addItem(MODEL_DESCRIPTIONS.get(model_name, model_name), userData=model_name)

        self.set_selected_model(default_model)

        layout = QHBoxLayout()
        layout.addWidget(QLabel("Modelo:"))
        layout.addWidget(self.combo, stretch=1)
        self.setLayout(layout)

    def selected_model(self) -> str:
        """Devuelve el identificador interno del modelo actualmente elegido."""
        return self.combo.currentData()

    def set_selected_model(self, model_name: str) -> None:
        """Selecciona programáticamente un modelo por su identificador."""
        index = self.combo.findData(model_name)
        if index >= 0:
            self.combo.setCurrentIndex(index)
