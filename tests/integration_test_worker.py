from __future__ import annotations
import os
import sys
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QTimer

from gui.worker import TranscriptionWorker

AUDIO_PATH = "/home/claude/work/test_audio.wav"
OUTPUT_DIR = "/home/claude/work/integration_output"


def fake_load_model(model_name, device):
    class FakeModel:
        def transcribe(self, path, fp16):
            return {
                "text": "Esta es una transcripción simulada de prueba.",
                "language": "es",
                "segments": [
                    {"id": 0, "start": 0.0, "end": 1.0, "text": "Esta es una"},
                    {"id": 1, "start": 1.0, "end": 2.0, "text": "transcripción simulada de prueba."},
                ],
            }

    return FakeModel()


def run() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    app = QCoreApplication(sys.argv)

    results_holder = {}

    def on_finished(audio_path, export_results):
        results_holder["audio_path"] = audio_path
        results_holder["export_results"] = export_results
        app.quit()

    def on_failed(message):
        results_holder["error"] = message
        app.quit()

    with patch("core.transcriber.load_model", side_effect=fake_load_model):
        worker = TranscriptionWorker(
            audio_path=AUDIO_PATH,
            model_name="base",
            output_formats=["txt", "md", "srt", "vtt", "json"],
            output_dir=OUTPUT_DIR,
        )
        worker.finished_ok.connect(on_finished)
        worker.failed.connect(on_failed)
        worker.progress.connect(lambda msg: print(f"[progress] {msg}"))
        worker.progress_percent.connect(lambda pct: print(f"[progress_percent] {pct:.1f}%"))
        worker.start()

        QTimer.singleShot(15000, app.quit)  # salvaguarda anti-cuelgue
        app.exec()

    if "error" in results_holder:
        print(f"❌ FALLÓ: {results_holder['error']}")
        sys.exit(1)

    export_results = results_holder.get("export_results")
    assert export_results is not None, "El worker no emitió resultados"

    print(f"\nResultados de exportación: {export_results}")

    for fmt, path in export_results.items():
        assert path is not None, f"El formato {fmt} falló"
        assert os.path.exists(path), f"El archivo {path} no existe"
        print(f"✔️ {fmt}: {path} ({os.path.getsize(path)} bytes)")

    # Validaciones de contenido específicas
    with open(export_results["txt"], encoding="utf-8") as f:
        assert "transcripción simulada" in f.read()
    with open(export_results["srt"], encoding="utf-8") as f:
        srt_content = f.read()
        assert "00:00:00,000 --> 00:00:01,000" in srt_content
    with open(export_results["vtt"], encoding="utf-8") as f:
        assert "WEBVTT" in f.read()

    import json as json_module
    with open(export_results["json"], encoding="utf-8") as f:
        data = json_module.load(f)
        assert data["model"] == "base"
        assert len(data["segments"]) == 2

    print("\n🎉 INTEGRATION TEST WORKER: TODO CORRECTO")


if __name__ == "__main__":
    run()
