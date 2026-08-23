import sys
import types
from unittest.mock import MagicMock

import pytest

from core.transcriber import VALID_MODELS, detect_device, load_model, transcribe_audio


# --- detect_device ---

def test_detect_device_returns_cpu_when_torch_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", None)
    # Forzar ImportError simulando ausencia real del módulo:
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "torch":
            raise ImportError("no torch")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert detect_device() == "cpu"


def test_detect_device_returns_cuda_when_available(monkeypatch):
    fake_torch = types.ModuleType("torch")
    fake_torch.cuda = MagicMock()
    fake_torch.cuda.is_available.return_value = True
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    assert detect_device() == "cuda"


def test_detect_device_returns_cpu_when_cuda_unavailable(monkeypatch):
    fake_torch = types.ModuleType("torch")
    fake_torch.cuda = MagicMock()
    fake_torch.cuda.is_available.return_value = False
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    assert detect_device() == "cpu"


# --- load_model ---

def test_load_model_rejects_invalid_model_name():
    with pytest.raises(ValueError, match="no válido"):
        load_model("not-a-model", device="cpu")


def test_load_model_raises_runtime_error_when_whisper_missing(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "whisper":
            raise ImportError("no whisper")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match="openai-whisper"):
        load_model("base", device="cpu")


def test_load_model_success(monkeypatch):
    fake_whisper = types.ModuleType("whisper")
    fake_model = MagicMock()
    fake_whisper.load_model = MagicMock(return_value=fake_model)
    monkeypatch.setitem(sys.modules, "whisper", fake_whisper)

    result = load_model("base", device="cpu")

    assert result is fake_model
    fake_whisper.load_model.assert_called_once_with("base", device="cpu")


def test_load_model_wraps_whisper_exceptions(monkeypatch):
    fake_whisper = types.ModuleType("whisper")

    def raise_error(*args, **kwargs):
        raise RuntimeError("checksum mismatch")

    fake_whisper.load_model = raise_error
    monkeypatch.setitem(sys.modules, "whisper", fake_whisper)

    with pytest.raises(RuntimeError, match="Error al cargar el modelo Whisper"):
        load_model("base", device="cpu")


def test_all_valid_models_are_accepted_by_validation():
    for model_name in VALID_MODELS:
        # No debe lanzar ValueError durante la validación de nombre.
        try:
            load_model(model_name, device="cpu")
        except ValueError:
            pytest.fail(f"'{model_name}' debería ser un nombre de modelo válido")
        except RuntimeError:
            pass  # esperado: whisper no está instalado en este entorno de test


# --- transcribe_audio ---

def test_transcribe_audio_calls_model_with_fp16_true_on_cuda():
    fake_model = MagicMock()
    fake_model.transcribe.return_value = {"text": "hola"}

    result = transcribe_audio(fake_model, "audio.mp3", device="cuda")

    fake_model.transcribe.assert_called_once_with("audio.mp3", fp16=True)
    assert result == {"text": "hola"}


def test_transcribe_audio_calls_model_with_fp16_false_on_cpu():
    fake_model = MagicMock()
    fake_model.transcribe.return_value = {"text": "hola"}

    transcribe_audio(fake_model, "audio.mp3", device="cpu")

    fake_model.transcribe.assert_called_once_with("audio.mp3", fp16=False)


def test_transcribe_audio_without_callback_does_not_touch_whisper_module():
    # Sin progress_callback no debe intentarse importar whisper.transcribe.
    fake_model = MagicMock()
    fake_model.transcribe.return_value = {"text": "hola"}

    result = transcribe_audio(fake_model, "audio.mp3", device="cpu", progress_callback=None)

    assert result == {"text": "hola"}
    fake_model.transcribe.assert_called_once_with("audio.mp3", fp16=False)


def test_transcribe_audio_reports_progress_via_callback(monkeypatch):
    # Simula el módulo whisper.transcribe con una barra tqdm mínima, tal
    # como la usa internamente Whisper para reportar avance por frames.
    class FakeTqdmBase:
        def __init__(self, total=None, **kwargs):
            self.total = total
            self.n = 0

        def update(self, n=1):
            self.n += n

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    fake_tqdm_pkg = types.ModuleType("tqdm")
    fake_tqdm_pkg.tqdm = FakeTqdmBase

    fake_whisper_transcribe = types.ModuleType("whisper.transcribe")
    fake_whisper_transcribe.tqdm = fake_tqdm_pkg

    fake_whisper_pkg = types.ModuleType("whisper")
    fake_whisper_pkg.transcribe = fake_whisper_transcribe

    monkeypatch.setitem(sys.modules, "whisper", fake_whisper_pkg)
    monkeypatch.setitem(sys.modules, "whisper.transcribe", fake_whisper_transcribe)

    def fake_model_transcribe(path, fp16):
        del path, fp16
        # Simula lo que hace Whisper por dentro: usa la tqdm parcheada.
        import whisper.transcribe as wt

        with wt.tqdm.tqdm(total=100) as pbar:
            pbar.update(40)
            pbar.update(60)
        return {"text": "ok"}

    fake_model = MagicMock()
    fake_model.transcribe.side_effect = fake_model_transcribe

    reported: list[float] = []
    result = transcribe_audio(
        fake_model, "audio.mp3", device="cpu", progress_callback=reported.append
    )

    assert result == {"text": "ok"}
    assert reported == [40.0, 100.0]
    # La clase tqdm original se restaura tras la llamada.
    assert fake_whisper_transcribe.tqdm.tqdm is FakeTqdmBase


def test_transcribe_audio_progress_callback_ignored_when_whisper_missing(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "whisper.transcribe" or name == "whisper":
            raise ImportError("no whisper")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    fake_model = MagicMock()
    fake_model.transcribe.return_value = {"text": "ok"}
    reported: list[float] = []

    result = transcribe_audio(
        fake_model, "audio.mp3", device="cpu", progress_callback=reported.append
    )

    assert result == {"text": "ok"}
    assert reported == []  # nunca se llamó, pero tampoco falló


def test_transcribe_audio_progress_callback_errors_are_swallowed(monkeypatch):
    class FakeTqdmBase:
        def __init__(self, total=None, **kwargs):
            self.total = total
            self.n = 0

        def update(self, n=1):
            self.n += n

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    fake_tqdm_pkg = types.ModuleType("tqdm")
    fake_tqdm_pkg.tqdm = FakeTqdmBase

    fake_whisper_transcribe = types.ModuleType("whisper.transcribe")
    fake_whisper_transcribe.tqdm = fake_tqdm_pkg

    fake_whisper_pkg = types.ModuleType("whisper")
    fake_whisper_pkg.transcribe = fake_whisper_transcribe

    monkeypatch.setitem(sys.modules, "whisper", fake_whisper_pkg)
    monkeypatch.setitem(sys.modules, "whisper.transcribe", fake_whisper_transcribe)

    def fake_model_transcribe(path, fp16):
        del path, fp16
        import whisper.transcribe as wt

        with wt.tqdm.tqdm(total=10) as pbar:
            pbar.update(5)  # el callback lanzará una excepción aquí
        return {"text": "ok"}

    fake_model = MagicMock()
    fake_model.transcribe.side_effect = fake_model_transcribe

    def broken_callback(_percentage):
        raise RuntimeError("callback roto")

    # No debe propagar la excepción del callback ni interrumpir la transcripción.
    result = transcribe_audio(
        fake_model, "audio.mp3", device="cpu", progress_callback=broken_callback
    )
    assert result == {"text": "ok"}
