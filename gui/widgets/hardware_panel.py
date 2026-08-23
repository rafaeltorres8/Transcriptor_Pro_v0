from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from core.hardware import ModelRecommendation, detect_hardware, recommend_model


class HardwarePanel(QGroupBox):
    """Muestra la RAM/VRAM detectadas y permite aplicar el modelo Whisper
    recomendado con un clic."""

    model_recommended = Signal(str)  # emite el nombre del modelo sugerido

    def __init__(self, parent=None) -> None:
        super().__init__("Hardware detectado", parent)

        self.hardware_label = QLabel("Detectando hardware…")
        self.recommendation_label = QLabel("")
        self.recommendation_label.setWordWrap(True)

        self.apply_button = QPushButton("Usar modelo recomendado")
        self.apply_button.clicked.connect(self._on_apply_clicked)

        info_layout = QVBoxLayout()
        info_layout.addWidget(self.hardware_label)
        info_layout.addWidget(self.recommendation_label)

        row = QHBoxLayout()
        row.addLayout(info_layout, stretch=1)
        row.addWidget(self.apply_button)
        self.setLayout(row)

        self._recommendation: ModelRecommendation | None = None
        self.refresh()

    def refresh(self) -> None:
        """Vuelve a detectar el hardware y recalcula la recomendación."""
        hardware = detect_hardware()
        self._recommendation = recommend_model(hardware)

        if hardware.gpu_available and hardware.total_vram_gb is not None:
            gpu_text = f"🎮 GPU: {hardware.gpu_name} ({hardware.total_vram_gb:.1f} GB VRAM)"
        else:
            gpu_text = "🎮 GPU: no detectada (se usará CPU)"

        ram_text = (
            f"🖥️ RAM: {hardware.total_ram_gb:.1f} GB"
            if hardware.ram_detected
            else "🖥️ RAM: no se pudo detectar"
        )
        self.hardware_label.setText(f"{ram_text}   |   {gpu_text}")
        self.recommendation_label.setText(
            f"💡 Modelo recomendado: <b>{self._recommendation.model_name}</b> — "
            f"{self._recommendation.reason}"
        )

    def _on_apply_clicked(self) -> None:
        if self._recommendation is not None:
            self.model_recommended.emit(self._recommendation.model_name)

    def recommended_model(self) -> str | None:
        """Devuelve el nombre del modelo actualmente recomendado, o `None`
        si aún no se ha calculado ninguna recomendación."""
        return self._recommendation.model_name if self._recommendation else None
