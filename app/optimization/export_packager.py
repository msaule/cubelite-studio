from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.config import version_string
from app.optimization.mesh_analyzer import MeshStats, analyze_mesh
from app.optimization.roblox_checker import RobloxReadinessReport
from app.utils.file_utils import copy_if_exists, safe_display_path, sanitize_prompt_for_path
from app.utils.time_utils import utc_iso, utc_timestamp

LICENSE_NOTE = (
    "This asset was generated using a workflow around Roblox Cube 3D. Users are responsible for following "
    "the original Cube 3D license and Roblox platform rules."
)


@dataclass
class ExportPackageResult:
    success: bool
    export_dir: str | None
    metadata_path: str | None
    notes_path: str | None
    error_message: str = ""


def create_export_package(
    prompt: str,
    profile_name: str,
    original_obj: Path,
    exports_root: Path,
    readiness: RobloxReadinessReport,
    original_stats: MeshStats | None = None,
    optimized_obj: Path | None = None,
    optimized_stats: MeshStats | None = None,
    preview_path: Path | None = None,
    inspection_plate_path: Path | None = None,
    benchmark_summary: dict[str, object] | None = None,
    dry_run: bool = False,
    cube_repo_path: Path | str | None = None,
    model_weights_path: Path | str | None = None,
    gpu_name: str = "",
    total_vram_gb: float | None = None,
    peak_vram_gb: float | None = None,
    generation_time_seconds: float | None = None,
    include_private_paths: bool = False,
) -> ExportPackageResult:
    try:
        if not original_obj.exists():
            return ExportPackageResult(False, None, None, None, "Original OBJ file does not exist.")
        export_dir = exports_root / f"{sanitize_prompt_for_path(prompt)}-{utc_timestamp()}"
        export_dir.mkdir(parents=True, exist_ok=False)

        copied_original = copy_if_exists(original_obj, export_dir / "original.obj")
        copied_optimized = copy_if_exists(optimized_obj, export_dir / "optimized.obj") if optimized_obj else None
        copy_if_exists(preview_path, export_dir / (preview_path.name if preview_path else "preview.png"))
        copied_plate = copy_if_exists(inspection_plate_path, export_dir / "inspection_plate.png") if inspection_plate_path else None

        original_stats = original_stats or analyze_mesh(original_obj)
        if copied_optimized and optimized_stats is None:
            optimized_stats = analyze_mesh(copied_optimized)

        metadata = {
            "prompt": prompt,
            "timestamp": utc_iso(),
            "profile": profile_name,
            "dry_run": dry_run,
            "cubelite_studio_version": version_string(),
            "cube_3d_repo_path_used": safe_display_path(cube_repo_path, include_private_paths),
            "model_weights_path_used": safe_display_path(model_weights_path, include_private_paths),
            "gpu_name": gpu_name,
            "total_vram_gb": total_vram_gb,
            "peak_vram_gb": peak_vram_gb,
            "generation_time_seconds": generation_time_seconds,
            "original_mesh_stats": original_stats.to_dict(),
            "optimized_mesh_stats": optimized_stats.to_dict() if optimized_stats else None,
            "inspection_plate": str(copied_plate.name) if copied_plate else None,
            "readiness_score": readiness.score,
            "readiness_status": readiness.status,
            "warnings": readiness.warnings,
            "license_note": LICENSE_NOTE,
        }

        metadata_path = export_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        notes_path = export_dir / "roblox_import_notes.txt"
        notes_path.write_text(readiness.to_text(), encoding="utf-8")
        summary_path = export_dir / "benchmark_summary.json"
        summary_path.write_text(json.dumps(benchmark_summary or {}, indent=2), encoding="utf-8")

        return ExportPackageResult(True, str(export_dir), str(metadata_path), str(notes_path))
    except Exception as exc:
        return ExportPackageResult(False, None, None, None, f"Export failed: {exc}")
