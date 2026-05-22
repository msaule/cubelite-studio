from __future__ import annotations

import platform
import sys
from dataclasses import asdict, dataclass

try:
    import psutil
except Exception:  # pragma: no cover - optional dependency fallback
    psutil = None

try:
    import torch
except Exception:  # pragma: no cover - optional dependency fallback
    torch = None

from app.cube.low_vram_profiles import recommend_profile


@dataclass
class SystemDiagnostics:
    os: str
    cpu: str
    ram_gb: float | None
    python_version: str
    pytorch_version: str
    cuda_available: bool
    cuda_version: str
    gpu_name: str
    total_vram_gb: float | None
    free_vram_gb: float | None
    used_vram_gb: float | None
    mps_available: bool
    recommended_profile: str
    warnings: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _bytes_to_gb(value: int | float | None) -> float | None:
    if value is None:
        return None
    return round(float(value) / (1024 ** 3), 2)


def _nvidia_memory() -> tuple[str, float | None, float | None, float | None]:
    try:
        import pynvml

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode("utf-8", errors="replace")
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        return str(name), _bytes_to_gb(mem.total), _bytes_to_gb(mem.free), _bytes_to_gb(mem.used)
    except Exception:
        return "", None, None, None


def detect_system() -> SystemDiagnostics:
    warnings: list[str] = []
    ram_gb = _bytes_to_gb(psutil.virtual_memory().total) if psutil else None
    pytorch_version = getattr(torch, "__version__", "not installed") if torch else "not installed"
    cuda_available = bool(torch and torch.cuda.is_available())
    cuda_version = str(getattr(torch.version, "cuda", "")) if torch else ""
    mps_available = bool(torch and hasattr(torch.backends, "mps") and torch.backends.mps.is_available())

    gpu_name = "No NVIDIA GPU detected"
    total_vram_gb: float | None = None
    free_vram_gb: float | None = None
    used_vram_gb: float | None = None

    if cuda_available:
        try:
            index = torch.cuda.current_device()
            gpu_name = torch.cuda.get_device_name(index)
            props = torch.cuda.get_device_properties(index)
            total_vram_gb = _bytes_to_gb(props.total_memory)
            try:
                free, total = torch.cuda.mem_get_info(index)
                free_vram_gb = _bytes_to_gb(free)
                total_vram_gb = _bytes_to_gb(total)
                used_vram_gb = round((total_vram_gb or 0) - (free_vram_gb or 0), 2)
            except Exception:
                pass
        except Exception as exc:
            warnings.append(f"PyTorch CUDA check failed: {exc}")

    nvml_name, nvml_total, nvml_free, nvml_used = _nvidia_memory()
    if nvml_name:
        gpu_name = nvml_name
        total_vram_gb = nvml_total if nvml_total is not None else total_vram_gb
        free_vram_gb = nvml_free if nvml_free is not None else free_vram_gb
        used_vram_gb = nvml_used if nvml_used is not None else used_vram_gb

    if not cuda_available:
        warnings.append("CUDA is not available through PyTorch. Real Cube 3D generation may be unavailable or CPU-only.")
    if total_vram_gb is not None and total_vram_gb < 16:
        warnings.append("Fast inference may require more VRAM than this machine has available.")

    recommended = recommend_profile(total_vram_gb).name
    return SystemDiagnostics(
        os=f"{platform.system()} {platform.release()}",
        cpu=platform.processor() or platform.machine(),
        ram_gb=ram_gb,
        python_version=sys.version.split()[0],
        pytorch_version=pytorch_version,
        cuda_available=cuda_available,
        cuda_version=cuda_version or "not available",
        gpu_name=gpu_name,
        total_vram_gb=total_vram_gb,
        free_vram_gb=free_vram_gb,
        used_vram_gb=used_vram_gb,
        mps_available=mps_available,
        recommended_profile=recommended,
        warnings=warnings,
    )
