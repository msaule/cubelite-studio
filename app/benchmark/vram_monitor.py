from __future__ import annotations

import threading
import time
from dataclasses import dataclass

try:
    import torch
except Exception:  # pragma: no cover - optional dependency fallback
    torch = None


@dataclass
class VRAMSnapshot:
    start_used_gb: float | None = None
    peak_used_gb: float | None = None
    end_used_gb: float | None = None
    peak_torch_allocated_gb: float | None = None
    duration_seconds: float = 0.0
    oom_status: bool = False


def _bytes_to_gb(value: int | float | None) -> float | None:
    if value is None:
        return None
    return round(float(value) / (1024 ** 3), 3)


class VRAMMonitor:
    def __init__(self, interval_seconds: float = 0.1) -> None:
        self.interval_seconds = interval_seconds
        self.snapshot = VRAMSnapshot()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._handle = None
        self._pynvml = None
        self._started = 0.0

    def __enter__(self) -> "VRAMMonitor":
        self._started = time.perf_counter()
        self._init_nvml()
        self.snapshot.start_used_gb = self._current_used()
        self.snapshot.peak_used_gb = self.snapshot.start_used_gb
        if torch and torch.cuda.is_available():
            try:
                torch.cuda.reset_peak_memory_stats()
            except Exception:
                pass
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        self.snapshot.end_used_gb = self._current_used()
        self.snapshot.duration_seconds = time.perf_counter() - self._started
        if torch and torch.cuda.is_available():
            try:
                self.snapshot.peak_torch_allocated_gb = _bytes_to_gb(torch.cuda.max_memory_allocated())
            except Exception:
                pass
        if exc is not None and "out of memory" in str(exc).lower():
            self.snapshot.oom_status = True

    def _init_nvml(self) -> None:
        try:
            import pynvml

            pynvml.nvmlInit()
            self._pynvml = pynvml
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception:
            self._pynvml = None
            self._handle = None

    def _current_used(self) -> float | None:
        if self._pynvml and self._handle:
            try:
                mem = self._pynvml.nvmlDeviceGetMemoryInfo(self._handle)
                return _bytes_to_gb(mem.used)
            except Exception:
                return None
        if torch and torch.cuda.is_available():
            try:
                return _bytes_to_gb(torch.cuda.memory_reserved())
            except Exception:
                return None
        return None

    def _poll(self) -> None:
        while not self._stop.is_set():
            current = self._current_used()
            if current is not None:
                if self.snapshot.peak_used_gb is None or current > self.snapshot.peak_used_gb:
                    self.snapshot.peak_used_gb = current
            time.sleep(self.interval_seconds)
