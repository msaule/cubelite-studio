from __future__ import annotations

import importlib.util
from dataclasses import dataclass


@dataclass
class DependencyStatus:
    name: str
    installed: bool
    required: bool
    purpose: str


DEPENDENCIES = [
    ("streamlit", True, "local app interface"),
    ("torch", False, "Cube 3D execution and CUDA diagnostics"),
    ("trimesh", True, "mesh analysis"),
    ("psutil", True, "system memory diagnostics"),
    ("pynvml", False, "NVIDIA VRAM tracking"),
    ("pymeshlab", False, "mesh simplification"),
    ("pandas", True, "benchmark tables"),
    ("plotly", False, "optional charts"),
]


def check_dependencies() -> list[DependencyStatus]:
    return [
        DependencyStatus(name=name, installed=importlib.util.find_spec(name) is not None, required=required, purpose=purpose)
        for name, required, purpose in DEPENDENCIES
    ]
