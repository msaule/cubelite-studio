from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path

from app.benchmark.vram_monitor import VRAMMonitor
from app.cube.cube_command_builder import build_cube_command
from app.cube.low_vram_profiles import GenerationProfile, resolve_auto_profile
from app.cube.model_manager import validate_cube_install
from app.system.gpu_detector import detect_system
from app.utils.file_utils import sanitize_prompt_for_path
from app.utils.process_utils import run_command
from app.utils.time_utils import utc_timestamp


@dataclass
class GenerationResult:
    success: bool
    prompt: str
    profile_name: str
    output_dir: str
    obj_path: str | None
    preview_path: str | None
    raw_logs: str
    error_message: str
    elapsed_seconds: float
    detected_gpu: str
    detected_total_vram_gb: float | None
    peak_vram_gb: float | None
    resolution_base_used: float
    fast_inference_used: bool
    dry_run: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def create_dry_run_obj(prompt: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    obj_path = output_dir / "generated.obj"
    # A small beveled-ish crate-like mesh: valid OBJ, intentionally simple.
    obj_text = """# CubeLite Studio dry-run sample mesh
o cubelite_dry_run_asset
v -0.5 -0.5 -0.5
v 0.5 -0.5 -0.5
v 0.5 0.5 -0.5
v -0.5 0.5 -0.5
v -0.5 -0.5 0.5
v 0.5 -0.5 0.5
v 0.5 0.5 0.5
v -0.5 0.5 0.5
vn 0 0 -1
vn 0 0 1
vn 0 -1 0
vn 0 1 0
vn -1 0 0
vn 1 0 0
f 1//1 2//1 3//1
f 1//1 3//1 4//1
f 5//2 7//2 6//2
f 5//2 8//2 7//2
f 1//3 6//3 2//3
f 1//3 5//3 6//3
f 4//4 3//4 7//4
f 4//4 7//4 8//4
f 1//5 4//5 8//5
f 1//5 8//5 5//5
f 2//6 6//6 7//6
f 2//6 7//6 3//6
"""
    obj_path.write_text(obj_text, encoding="utf-8")
    (output_dir / "dry_run_prompt.txt").write_text(prompt, encoding="utf-8")
    return obj_path


def _find_newest_obj(output_dir: Path) -> Path | None:
    objs = sorted(output_dir.rglob("*.obj"), key=lambda path: path.stat().st_mtime, reverse=True)
    return objs[0] if objs else None


def _friendly_error(logs: str, fallback: str) -> str:
    lower = logs.lower()
    if "out of memory" in lower or "cuda oom" in lower:
        return "Generation ran out of VRAM. Try Low VRAM mode, turn off preview generation, lower resolution, or close other GPU-heavy apps."
    if "no such file" in lower or "not found" in lower:
        return "Cube generation failed because a required file was missing. Check the Cube 3D repo path and model weights path."
    return fallback


def generate_mesh(
    prompt: str,
    profile: GenerationProfile,
    cube_repo_path: Path | str | None,
    model_weights_path: Path | str | None,
    output_dir: Path,
    dry_run: bool = False,
) -> GenerationResult:
    diagnostics = detect_system()
    resolved_profile = resolve_auto_profile(profile, diagnostics.total_vram_gb)
    run_dir = output_dir / f"{sanitize_prompt_for_path(prompt)}-{utc_timestamp()}"
    started = time.perf_counter()

    if dry_run:
        obj_path = create_dry_run_obj(prompt, run_dir)
        elapsed = time.perf_counter() - started
        return GenerationResult(
            success=True,
            prompt=prompt,
            profile_name=resolved_profile.name,
            output_dir=str(run_dir),
            obj_path=str(obj_path),
            preview_path=None,
            raw_logs="Dry run mode uses a sample mesh and does not call Cube 3D.",
            error_message="",
            elapsed_seconds=elapsed,
            detected_gpu=diagnostics.gpu_name,
            detected_total_vram_gb=diagnostics.total_vram_gb,
            peak_vram_gb=diagnostics.used_vram_gb,
            resolution_base_used=resolved_profile.resolution_base,
            fast_inference_used=resolved_profile.fast_inference,
            dry_run=True,
        )

    install = validate_cube_install(cube_repo_path, model_weights_path)
    if not install.ready_for_real_generation:
        elapsed = time.perf_counter() - started
        return GenerationResult(
            success=False,
            prompt=prompt,
            profile_name=resolved_profile.name,
            output_dir=str(run_dir),
            obj_path=None,
            preview_path=None,
            raw_logs="\n".join(install.messages),
            error_message=install.messages[0] if install.messages else "Cube 3D is not configured.",
            elapsed_seconds=elapsed,
            detected_gpu=diagnostics.gpu_name,
            detected_total_vram_gb=diagnostics.total_vram_gb,
            peak_vram_gb=None,
            resolution_base_used=resolved_profile.resolution_base,
            fast_inference_used=resolved_profile.fast_inference,
            dry_run=False,
        )

    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        command = build_cube_command(
            prompt=prompt,
            profile=resolved_profile,
            cube_repo_path=install.cube_repo_path or Path("."),
            model_weights_path=install.model_weights_path or Path("."),
            output_dir=run_dir,
        )
        with VRAMMonitor() as monitor:
            process_result = run_command(command.command, cwd=command.cwd)
        obj_path = _find_newest_obj(run_dir)
        logs = process_result.combined_logs
        if process_result.returncode != 0:
            return GenerationResult(
                success=False,
                prompt=prompt,
                profile_name=resolved_profile.name,
                output_dir=str(run_dir),
                obj_path=str(obj_path) if obj_path else None,
                preview_path=None,
                raw_logs=logs,
                error_message=_friendly_error(logs, "Cube 3D generation failed. See logs for details."),
                elapsed_seconds=process_result.elapsed_seconds,
                detected_gpu=diagnostics.gpu_name,
                detected_total_vram_gb=diagnostics.total_vram_gb,
                peak_vram_gb=monitor.snapshot.peak_used_gb,
                resolution_base_used=resolved_profile.resolution_base,
                fast_inference_used=resolved_profile.fast_inference,
                dry_run=False,
            )
        if obj_path is None:
            return GenerationResult(
                success=False,
                prompt=prompt,
                profile_name=resolved_profile.name,
                output_dir=str(run_dir),
                obj_path=None,
                preview_path=None,
                raw_logs=logs,
                error_message="Cube generation completed but no .obj file was found in the output folder.",
                elapsed_seconds=process_result.elapsed_seconds,
                detected_gpu=diagnostics.gpu_name,
                detected_total_vram_gb=diagnostics.total_vram_gb,
                peak_vram_gb=monitor.snapshot.peak_used_gb,
                resolution_base_used=resolved_profile.resolution_base,
                fast_inference_used=resolved_profile.fast_inference,
                dry_run=False,
            )
        return GenerationResult(
            success=True,
            prompt=prompt,
            profile_name=resolved_profile.name,
            output_dir=str(run_dir),
            obj_path=str(obj_path),
            preview_path=None,
            raw_logs=logs,
            error_message="",
            elapsed_seconds=process_result.elapsed_seconds,
            detected_gpu=diagnostics.gpu_name,
            detected_total_vram_gb=diagnostics.total_vram_gb,
            peak_vram_gb=monitor.snapshot.peak_used_gb,
            resolution_base_used=resolved_profile.resolution_base,
            fast_inference_used=resolved_profile.fast_inference,
            dry_run=False,
        )
    except Exception as exc:
        elapsed = time.perf_counter() - started
        return GenerationResult(
            success=False,
            prompt=prompt,
            profile_name=resolved_profile.name,
            output_dir=str(run_dir),
            obj_path=None,
            preview_path=None,
            raw_logs=str(exc),
            error_message=_friendly_error(str(exc), f"Cube 3D generation could not start: {exc}"),
            elapsed_seconds=elapsed,
            detected_gpu=diagnostics.gpu_name,
            detected_total_vram_gb=diagnostics.total_vram_gb,
            peak_vram_gb=None,
            resolution_base_used=resolved_profile.resolution_base,
            fast_inference_used=resolved_profile.fast_inference,
            dry_run=False,
        )
