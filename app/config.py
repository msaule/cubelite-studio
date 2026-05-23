from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app import __version__

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
EXPORTS_DIR = PROJECT_ROOT / "exports"
REPORTS_DIR = PROJECT_ROOT / "reports"
BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks"
SAMPLE_ASSETS_DIR = PROJECT_ROOT / "sample_assets"
SETTINGS_PATH = PROJECT_ROOT / ".cubelite_settings.json"


@dataclass
class AppSettings:
    cube_repo_path: str = ""
    model_weights_path: str = ""
    outputs_dir: str = str(OUTPUTS_DIR)
    exports_dir: str = str(EXPORTS_DIR)
    reports_dir: str = str(REPORTS_DIR)
    benchmarks_dir: str = str(BENCHMARKS_DIR)
    default_profile: str = "Auto"
    default_target_face_count: int = 10000
    texture_provider: str = "studio"
    texture_model_id: str = "hf-internal-testing/tiny-stable-diffusion-pipe"
    texture_steps: int = 8
    texture_size: int = 1024
    include_private_paths_in_reports: bool = False


def ensure_project_dirs() -> None:
    for path in (OUTPUTS_DIR, EXPORTS_DIR, REPORTS_DIR, BENCHMARKS_DIR, SAMPLE_ASSETS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def load_settings(path: Path = SETTINGS_PATH) -> AppSettings:
    if not path.exists():
        return AppSettings()
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppSettings()
    defaults = asdict(AppSettings())
    defaults.update({k: v for k, v in data.items() if k in defaults})
    return AppSettings(**defaults)


def save_settings(settings: AppSettings, path: Path = SETTINGS_PATH) -> None:
    path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")


def version_string() -> str:
    return __version__
