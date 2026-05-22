from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from app.cube.low_vram_profiles import GenerationProfile


@dataclass
class CubeCommand:
    command: list[str]
    cwd: Path
    unsupported_settings: list[str]
    notes: list[str]


def _load_template(repo_path: Path) -> list[str] | None:
    template_path = repo_path / "cubelite_cube_command.json"
    if not template_path.exists():
        return None
    data = json.loads(template_path.read_text(encoding="utf-8"))
    template = data.get("command")
    if not isinstance(template, list) or not all(isinstance(part, str) for part in template):
        raise ValueError("cubelite_cube_command.json must contain a string list field named 'command'.")
    return template


def build_cube_command(
    prompt: str,
    profile: GenerationProfile,
    cube_repo_path: Path,
    model_weights_path: Path,
    output_dir: Path,
) -> CubeCommand:
    """Build a safe Cube command.

    Cube 3D command-line flags can change between releases. CubeLite therefore
    uses an explicit template file instead of pretending every profile knob maps
    to a supported CLI flag.
    """
    template = _load_template(cube_repo_path)
    if template is None:
        raise FileNotFoundError(
            "No cubelite_cube_command.json was found in the Cube 3D repo. Add one with a command array using placeholders."
        )

    replacements = {
        "{python}": sys.executable,
        "{prompt}": prompt,
        "{output_dir}": str(output_dir),
        "{weights_path}": str(model_weights_path),
        "{gpt_ckpt_path}": str(model_weights_path / "shape_gpt.safetensors"),
        "{shape_ckpt_path}": str(model_weights_path / "shape_tokenizer.safetensors"),
        "{resolution_base}": str(profile.resolution_base),
        "{fast_inference}": "true" if profile.fast_inference else "false",
        "{fp16}": "true" if profile.use_fp16 else "false",
        "{cpu_offload}": "true" if profile.enable_cpu_offload else "false",
        "{guidance_scale}": str(profile.guidance_scale),
        "{use_kv_cache}": "true" if profile.use_kv_cache else "false",
        "{decoder_chunk_size}": str(profile.decoder_chunk_size),
        "{inference_dtype}": profile.inference_dtype,
    }
    command: list[str] = []
    for part in template:
        resolved = part
        for placeholder, value in replacements.items():
            resolved = resolved.replace(placeholder, value)
        command.append(resolved)

    unsupported = [
        "generate_preview",
        "simplify_after_generation",
        "target_face_count",
        "bounding_box_xyz",
    ]
    notes = [
        "Profile settings are passed only when the command template includes their placeholders.",
        "Settings not understood by the detected Cube install are treated as CubeLite post-processing preferences.",
    ]
    return CubeCommand(command=command, cwd=cube_repo_path, unsupported_settings=unsupported, notes=notes)
