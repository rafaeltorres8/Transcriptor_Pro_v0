import sys
import types
from unittest.mock import MagicMock

import pytest

from core.hardware import (
    HardwareInfo,
    ModelRecommendation,
    detect_hardware,
    detect_ram_gb,
    detect_vram_gb,
    recommend_model,
)


def _hw(ram_gb=0.0, ram_detected=True, vram_gb=None, gpu_name=None):
    return HardwareInfo(
        total_ram_gb=ram_gb,
        ram_detected=ram_detected,
        gpu_available=vram_gb is not None,
        total_vram_gb=vram_gb,
        gpu_name=gpu_name,
    )


# --- detect_ram_gb ---

def test_detect_ram_gb_returns_zero_when_psutil_missing(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "psutil":
            raise ImportError("no psutil")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    total_gb, detected = detect_ram_gb()
    assert total_gb == 0.0
    assert detected is False


def test_detect_ram_gb_returns_value_from_psutil(monkeypatch):
    fake_psutil = types.ModuleType("psutil")
    fake_vm = MagicMock()
    fake_vm.total = 16 * (1024**3)
    fake_psutil.virtual_memory = MagicMock(return_value=fake_vm)
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    total_gb, detected = detect_ram_gb()
    assert detected is True
    assert total_gb == pytest.approx(16.0)


def test_detect_ram_gb_handles_unexpected_errors(monkeypatch):
    fake_psutil = types.ModuleType("psutil")

    def raise_error():
        raise RuntimeError("boom")

    fake_psutil.virtual_memory = raise_error
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    total_gb, detected = detect_ram_gb()
    assert total_gb == 0.0
    assert detected is False


# --- detect_vram_gb ---

def test_detect_vram_gb_returns_none_when_torch_missing(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "torch":
            raise ImportError("no torch")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    total_gb, name = detect_vram_gb()
    assert total_gb is None
    assert name is None


def test_detect_vram_gb_returns_none_when_cuda_unavailable(monkeypatch):
    fake_torch = types.ModuleType("torch")
    fake_torch.cuda = MagicMock()
    fake_torch.cuda.is_available.return_value = False
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    total_gb, name = detect_vram_gb()
    assert total_gb is None
    assert name is None


def test_detect_vram_gb_returns_value_when_cuda_available(monkeypatch):
    fake_torch = types.ModuleType("torch")
    fake_torch.cuda = MagicMock()
    fake_torch.cuda.is_available.return_value = True
    fake_props = MagicMock()
    fake_props.total_memory = 8 * (1024**3)
    fake_props.name = "Fake GPU 3000"
    fake_torch.cuda.get_device_properties.return_value = fake_props
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    total_gb, name = detect_vram_gb()
    assert total_gb == pytest.approx(8.0)
    assert name == "Fake GPU 3000"


def test_detect_vram_gb_handles_unexpected_errors(monkeypatch):
    fake_torch = types.ModuleType("torch")
    fake_torch.cuda = MagicMock()
    fake_torch.cuda.is_available.return_value = True
    fake_torch.cuda.get_device_properties.side_effect = RuntimeError("boom")
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    total_gb, name = detect_vram_gb()
    assert total_gb is None
    assert name is None


# --- detect_hardware ---

def test_detect_hardware_combines_ram_and_vram(monkeypatch):
    import core.hardware as mod

    monkeypatch.setattr(mod, "detect_ram_gb", lambda: (16.0, True))
    monkeypatch.setattr(mod, "detect_vram_gb", lambda: (8.0, "Fake GPU"))

    hw = detect_hardware()
    assert hw.total_ram_gb == 16.0
    assert hw.ram_detected is True
    assert hw.gpu_available is True
    assert hw.total_vram_gb == 8.0
    assert hw.gpu_name == "Fake GPU"


# --- recommend_model: con GPU (basado en VRAM oficial) ---

@pytest.mark.parametrize(
    "vram_gb, expected_model",
    [
        (0.5, "tiny"),
        (1.0, "base"),
        (2.0, "small"),
        (5.0, "medium"),
        (6.0, "turbo"),
        (10.0, "large"),
        (24.0, "large"),
    ],
)
def test_recommend_model_uses_vram_when_gpu_available(vram_gb, expected_model):
    hw = _hw(ram_gb=32.0, vram_gb=vram_gb, gpu_name="Fake GPU")
    recommendation = recommend_model(hw)

    assert isinstance(recommendation, ModelRecommendation)
    assert recommendation.model_name == expected_model
    assert "GPU" in recommendation.reason


# --- recommend_model: sin GPU (basado en RAM con margen) ---

def test_recommend_model_falls_back_to_ram_when_no_gpu():
    # Requisito de CPU para 'small': (2 GB * factor 2) + 2 GB overhead = 6 GB
    hw = _hw(ram_gb=6.0, ram_detected=True, vram_gb=None)
    recommendation = recommend_model(hw)
    assert recommendation.model_name == "small"
    assert "RAM" in recommendation.reason


def test_recommend_model_low_ram_recommends_tiny():
    hw = _hw(ram_gb=2.0, ram_detected=True, vram_gb=None)
    recommendation = recommend_model(hw)
    assert recommendation.model_name == "tiny"


def test_recommend_model_high_ram_recommends_large():
    # Requisito de CPU para 'large': (10 GB * factor 2) + 2 GB overhead = 22 GB
    hw = _hw(ram_gb=64.0, ram_detected=True, vram_gb=None)
    recommendation = recommend_model(hw)
    assert recommendation.model_name == "large"


def test_recommend_model_ram_not_detected_defaults_to_tiny():
    hw = _hw(ram_gb=0.0, ram_detected=False, vram_gb=None)
    recommendation = recommend_model(hw)
    assert recommendation.model_name == "tiny"
    assert "psutil" in recommendation.reason


def test_recommend_model_uses_detect_hardware_when_none_given(monkeypatch):
    import core.hardware as mod

    fake_hw = _hw(ram_gb=8.0, vram_gb=None)
    monkeypatch.setattr(mod, "detect_hardware", lambda: fake_hw)

    recommendation = recommend_model()
    assert recommendation.hardware == fake_hw
