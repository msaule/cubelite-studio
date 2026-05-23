from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.benchmark.benchmark_models import BenchmarkRow
from app.benchmark.benchmark_prompts import BENCHMARK_PROMPTS
from app.benchmark.benchmark_report import generate_technical_report
from app.config import BENCHMARKS_DIR, EXPORTS_DIR, OUTPUTS_DIR, REPORTS_DIR
from app.cube.cube_runner import generate_mesh
from app.cube.low_vram_profiles import GenerationProfile, get_profile
from app.optimization.asset_finisher import finish_asset_for_roblox
from app.optimization.export_packager import create_export_package
from app.optimization.mesh_analyzer import analyze_mesh
from app.optimization.mesh_renderer import render_mesh_inspection_plate, render_mesh_preview
from app.optimization.mesh_simplifier import simplify_mesh
from app.optimization.roblox_checker import check_roblox_readiness
from app.system.gpu_detector import detect_system
from app.utils.time_utils import utc_timestamp


@dataclass
class BenchmarkResult:
    rows: list[BenchmarkRow]
    csv_path: str
    json_path: str
    report_path: str | None


ProgressCallback = Callable[[BenchmarkRow], None]


def _write_rows(rows: list[BenchmarkRow], benchmarks_dir: Path) -> tuple[Path, Path]:
    benchmarks_dir.mkdir(parents=True, exist_ok=True)
    csv_path = benchmarks_dir / f"benchmark-results-{utc_timestamp()}.csv"
    json_path = benchmarks_dir / f"benchmark-results-{utc_timestamp()}.json"
    fieldnames = list(BenchmarkRow("", "", False, 0.0, None, None, None, None, "", None).to_dict().keys())
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())
    json_path.write_text(json.dumps([row.to_dict() for row in rows], indent=2), encoding="utf-8")
    return csv_path, json_path


def run_single_pipeline(
    prompt: str,
    profile: GenerationProfile,
    cube_repo_path: Path | str | None,
    model_weights_path: Path | str | None,
    outputs_dir: Path = OUTPUTS_DIR,
    exports_dir: Path = EXPORTS_DIR,
    dry_run: bool = True,
    package_export: bool = True,
    simplify: bool | None = None,
    texture_provider: str = "procedural",
    texture_model_id: str | None = None,
    texture_steps: int = 8,
    texture_size: int = 1024,
    texture_seed: int = 0,
) -> tuple[BenchmarkRow, dict[str, object]]:
    generation = generate_mesh(
        prompt=prompt,
        profile=profile,
        cube_repo_path=cube_repo_path,
        model_weights_path=model_weights_path,
        output_dir=outputs_dir,
        dry_run=dry_run,
    )
    obj_path = Path(generation.obj_path) if generation.obj_path else None
    stats = analyze_mesh(obj_path) if obj_path else None

    optimized_stats = None
    optimized_obj = None
    simplification_result = None
    render_result = None
    inspection_result = None
    finish_result = None
    simplify_requested = profile.simplify_after_generation if simplify is None else simplify
    if obj_path and stats and stats.success and simplify_requested:
        optimized_obj = Path(generation.output_dir) / "optimized.obj"
        simplification_result = simplify_mesh(obj_path, optimized_obj, profile.target_face_count)
        if simplification_result.output_path:
            optimized_stats = analyze_mesh(Path(simplification_result.output_path))

    render_source = optimized_obj if optimized_obj and optimized_obj.exists() else obj_path
    preview_path = None
    if render_source and stats and stats.success:
        preview_path = Path(generation.output_dir) / "preview.png"
        render_result = render_mesh_preview(render_source, preview_path, title=prompt)
        if not render_result.success:
            preview_path = None
        inspection_plate_path = Path(generation.output_dir) / "inspection_plate.png"
        inspection_result = render_mesh_inspection_plate(render_source, inspection_plate_path, title=prompt)
        if not inspection_result.success:
            inspection_plate_path = None
    else:
        inspection_plate_path = None

    if render_source and stats and stats.success:
        finish_dir = Path(generation.output_dir) / "finished_asset"
        finish_result = finish_asset_for_roblox(
            render_source,
            finish_dir,
            prompt=prompt,
            texture_provider=texture_provider,
            texture_model_id=texture_model_id,
            texture_steps=texture_steps,
            texture_size=texture_size,
            texture_seed=texture_seed,
        )

    readiness = check_roblox_readiness(
        optimized_stats if optimized_stats and optimized_stats.success else (stats or analyze_mesh(Path("__missing__.obj"))),
        simplification_failed=bool(simplification_result and not simplification_result.success),
    )

    export_result = None
    if package_export and obj_path and stats:
        export_result = create_export_package(
            prompt=prompt,
            profile_name=generation.profile_name,
            original_obj=obj_path,
            exports_root=exports_dir,
            readiness=readiness,
            original_stats=stats,
            optimized_obj=optimized_obj if optimized_obj and optimized_obj.exists() else None,
            optimized_stats=optimized_stats,
            preview_path=preview_path,
            inspection_plate_path=inspection_plate_path,
            finished_asset=finish_result.to_dict() if finish_result else None,
            dry_run=dry_run,
            cube_repo_path=cube_repo_path,
            model_weights_path=model_weights_path,
            gpu_name=generation.detected_gpu,
            total_vram_gb=generation.detected_total_vram_gb,
            peak_vram_gb=generation.peak_vram_gb,
            generation_time_seconds=generation.elapsed_seconds,
        )

    row = BenchmarkRow(
        prompt=prompt,
        profile=generation.profile_name,
        success=bool(generation.success and stats and stats.success),
        generation_time_seconds=generation.elapsed_seconds,
        peak_vram_gb=generation.peak_vram_gb,
        output_file_size_mb=stats.file_size_mb if stats else None,
        triangle_count=stats.triangle_count if stats else None,
        readiness_score=readiness.score,
        error_message=generation.error_message or (stats.error_message if stats and not stats.success else ""),
        output_path=export_result.export_dir if export_result and export_result.success else generation.output_dir,
    )
    details = {
        "generation": generation.to_dict(),
        "mesh_stats": stats.to_dict() if stats else None,
        "optimized_mesh_stats": optimized_stats.to_dict() if optimized_stats else None,
        "simplification": simplification_result.to_dict() if simplification_result else None,
        "render": render_result.to_dict() if render_result else None,
        "inspection_render": inspection_result.to_dict() if inspection_result else None,
        "finished_asset": finish_result.to_dict() if finish_result else None,
        "readiness": readiness.to_dict(),
        "export": export_result.__dict__ if export_result else None,
    }
    return row, details


def run_benchmark(
    prompts: list[str] | None = None,
    profile_names: list[str] | None = None,
    max_prompts: int | None = None,
    dry_run: bool = True,
    cube_repo_path: Path | str | None = None,
    model_weights_path: Path | str | None = None,
    benchmarks_dir: Path = BENCHMARKS_DIR,
    outputs_dir: Path = OUTPUTS_DIR,
    exports_dir: Path = EXPORTS_DIR,
    reports_dir: Path = REPORTS_DIR,
    create_report: bool = True,
    texture_provider: str = "procedural",
    texture_model_id: str | None = None,
    texture_steps: int = 8,
    texture_size: int = 1024,
    on_row: ProgressCallback | None = None,
) -> BenchmarkResult:
    selected_prompts = list(prompts or BENCHMARK_PROMPTS)
    if max_prompts:
        selected_prompts = selected_prompts[:max_prompts]
    selected_profiles = [get_profile(name) for name in (profile_names or ["Low VRAM", "Balanced"])]

    rows: list[BenchmarkRow] = []
    for prompt in selected_prompts:
        for profile in selected_profiles:
            try:
                row, _ = run_single_pipeline(
                    prompt=prompt,
                    profile=profile,
                    cube_repo_path=cube_repo_path,
                    model_weights_path=model_weights_path,
                    outputs_dir=outputs_dir,
                    exports_dir=exports_dir,
                    dry_run=dry_run,
                    package_export=True,
                    texture_provider=texture_provider,
                    texture_model_id=texture_model_id,
                    texture_steps=texture_steps,
                    texture_size=texture_size,
                )
            except Exception as exc:
                row = BenchmarkRow(
                    prompt=prompt,
                    profile=profile.name,
                    success=False,
                    generation_time_seconds=0.0,
                    peak_vram_gb=None,
                    output_file_size_mb=None,
                    triangle_count=None,
                    readiness_score=None,
                    error_message=f"Benchmark run failed: {exc}",
                    output_path=None,
                )
            rows.append(row)
            if on_row:
                on_row(row)

    csv_path, json_path = _write_rows(rows, benchmarks_dir)
    report_path = None
    if create_report:
        report_path = generate_technical_report(
            rows=rows,
            diagnostics=detect_system(),
            profiles=selected_profiles,
            prompts=selected_prompts,
            reports_dir=reports_dir,
        )
    return BenchmarkResult(
        rows=rows,
        csv_path=str(csv_path),
        json_path=str(json_path),
        report_path=str(report_path) if report_path else None,
    )
