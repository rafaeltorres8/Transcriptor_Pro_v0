from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from gui.main_window import MainWindow

def run() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()

    # 1. Los paneles existen y están conectados.
    assert window.ffmpeg_panel is not None
    assert window.file_panel is not None
    assert window.hardware_panel is not None
    assert window.model_panel is not None
    assert window.format_panel is not None
    assert window.log_panel is not None
    print("✔️ Paneles instanciados correctamente")

    # 2. El panel de modelo tiene un valor por defecto válido.
    from core.transcriber import VALID_MODELS
    assert window.model_panel.selected_model() in VALID_MODELS
    print(f"✔️ Modelo por defecto válido: {window.model_panel.selected_model()}")

    # 2b. El panel de hardware calcula una recomendación válida y, al
    # aplicarla, el panel de modelo la refleja.
    recommended = window.hardware_panel.recommended_model()
    assert recommended in VALID_MODELS
    window.hardware_panel._on_apply_clicked()  # pylint: disable=protected-access
    assert window.model_panel.selected_model() == recommended
    print(f"✔️ Recomendación de hardware aplicada correctamente: {recommended}")

    # 2c. La barra de progreso del log arranca indeterminada y pasa a
    # mostrar un porcentaje real cuando llega un valor.
    window.log_panel.set_busy(True)
    assert window.log_panel.progress_bar.maximum() == 0  # indeterminada
    window.log_panel.set_progress_percent(42.0)
    assert window.log_panel.progress_bar.maximum() == 100
    assert window.log_panel.progress_bar.value() == 42
    window.log_panel.set_busy(False)
    print("✔️ Barra de progreso: modo indeterminado -> porcentaje real funciona")

    # 3. El panel de formatos devuelve una lista de formatos válidos.
    formats = window.format_panel.selected_formats()
    assert isinstance(formats, list)
    assert set(formats).issubset({"txt", "md", "srt", "vtt", "json"})
    print(f"✔️ Formatos seleccionados por defecto: {formats}")

    # 4. Cambiar la selección de formatos se refleja correctamente.
    window.format_panel.set_selected_formats(["srt", "vtt"])
    assert set(window.format_panel.selected_formats()) == {"srt", "vtt"}
    print("✔️ set_selected_formats / selected_formats funcionan correctamente")

    # 5. El panel de archivo detecta correctamente archivo inexistente.
    window.file_panel.set_file("/no/existe/audio.mp3")
    assert window.file_panel.is_valid() is False
    print("✔️ Detección de archivo inexistente funciona")

    # 6. Simular clic en "Transcribir" sin FFmpeg listo -> no debe crashear.
    # Se parchea QMessageBox.warning para que no bloquee esperando un clic real.
    original_warning = QMessageBox.warning
    QMessageBox.warning = staticmethod(lambda *a, **k: None)
    try:
        window.ffmpeg_panel._current_path = ""  # forzar estado no listo
        window._on_transcribe_clicked()
    finally:
        QMessageBox.warning = original_warning
    print("✔️ Clic en Transcribir sin FFmpeg listo no lanza excepción")

    # 7. Ventana se puede mostrar y cerrar sin errores.
    window.show()
    window.close()
    print("✔️ Ventana se muestra y cierra correctamente")

    print("\n🎉 SMOKE TEST GUI: TODO CORRECTO")


if __name__ == "__main__":
    run()
