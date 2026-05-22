from __future__ import annotations

from app.system.dependency_checker import check_dependencies
from app.system.gpu_detector import detect_system


def full_diagnostics() -> dict[str, object]:
    return {
        "system": detect_system().to_dict(),
        "dependencies": [status.__dict__ for status in check_dependencies()],
    }
