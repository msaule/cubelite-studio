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
    finished_asset: dict[str, object] | None = None,
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
        copied_textured_obj = _copy_finished_file(finished_asset, "textured_obj_path", export_dir / "textured.obj")
        copied_material = _copy_finished_file(finished_asset, "material_path", export_dir / "textured.mtl")
        copied_texture = _copy_finished_file(finished_asset, "texture_path", export_dir / "albedo.png")
        copied_normal = _copy_finished_file(finished_asset, "normal_path", export_dir / "normal.png")
        copied_roughness = _copy_finished_file(finished_asset, "roughness_path", export_dir / "roughness.png")
        copied_metallic = _copy_finished_file(finished_asset, "metallic_path", export_dir / "metallic.png")
        copied_semantic_obj = _copy_finished_file(finished_asset, "semantic_obj_path", export_dir / "semantic_material.obj")
        copied_semantic_mtl = _copy_finished_file(finished_asset, "semantic_material_path", export_dir / "semantic_material.mtl")
        copied_material_preview = _copy_finished_file(finished_asset, "material_preview_path", export_dir / "semantic_material_preview.png")
        copied_finish_report = _copy_finished_file(finished_asset, "report_path", export_dir / "finish_report.json")

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
            "original_mesh_stats": _stats_for_metadata(original_stats, include_private_paths),
            "optimized_mesh_stats": _stats_for_metadata(optimized_stats, include_private_paths) if optimized_stats else None,
            "inspection_plate": str(copied_plate.name) if copied_plate else None,
            "textured_obj": str(copied_textured_obj.name) if copied_textured_obj else None,
            "material_file": str(copied_material.name) if copied_material else None,
            "texture_file": str(copied_texture.name) if copied_texture else None,
            "normal_file": str(copied_normal.name) if copied_normal else None,
            "roughness_file": str(copied_roughness.name) if copied_roughness else None,
            "metallic_file": str(copied_metallic.name) if copied_metallic else None,
            "semantic_material_obj": str(copied_semantic_obj.name) if copied_semantic_obj else None,
            "semantic_material_file": str(copied_semantic_mtl.name) if copied_semantic_mtl else None,
            "semantic_material_preview": str(copied_material_preview.name) if copied_material_preview else None,
            "finish_report": str(copied_finish_report.name) if copied_finish_report else None,
            "texture_quality": (finished_asset or {}).get("texture_stats") if finished_asset else None,
            "semantic_material": (finished_asset or {}).get("semantic_material") if finished_asset else None,
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


def _copy_finished_file(finished_asset: dict[str, object] | None, key: str, destination: Path) -> Path | None:
    if not finished_asset:
        return None
    value = finished_asset.get(key)
    if not value:
        return None
    return copy_if_exists(Path(str(value)), destination)


def _stats_for_metadata(stats: MeshStats, include_private_paths: bool) -> dict[str, object]:
    data = stats.to_dict()
    if not include_private_paths and data.get("path"):
        data["path"] = Path(str(data["path"])).name
    return data
