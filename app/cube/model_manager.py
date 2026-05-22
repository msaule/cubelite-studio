from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class CubeInstallStatus:
    cube_repo_path: Path | None
    model_weights_path: Path | None
    repo_exists: bool
    weights_exist: bool
    command_template_exists: bool
    messages: list[str]

    @property
    def ready_for_real_generation(self) -> bool:
        return self.repo_exists and self.weights_exist


def _clean_path(value: str | Path | None) -> Path | None:
    if not value:
        return None
    return Path(value).expanduser()


def validate_cube_install(cube_repo_path: str | Path | None, model_weights_path: str | Path | None) -> CubeInstallStatus:
    repo = _clean_path(cube_repo_path)
    weights = _clean_path(model_weights_path)
    messages: list[str] = []

    repo_exists = bool(repo and repo.exists() and repo.is_dir())
    weights_exist = bool(weights and weights.exists())
    command_template_exists = bool(repo and (repo / "cubelite_cube_command.json").exists())

    if not repo_exists:
        messages.append("Cube 3D repo was not found. Set the local Cube 3D folder path in Settings.")
    if not weights_exist:
        messages.append("Cube 3D model weights were not found. Download them from the official source and select the folder here.")
    if repo_exists and not command_template_exists:
        messages.append(
            "No cubelite_cube_command.json template found. Real generation is available only when an explicit Cube command template is configured."
        )

    return CubeInstallStatus(
        cube_repo_path=repo,
        model_weights_path=weights,
        repo_exists=repo_exists,
        weights_exist=weights_exist,
        command_template_exists=command_template_exists,
        messages=messages,
    )
