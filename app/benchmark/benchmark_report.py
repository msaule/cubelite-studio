from __future__ import annotations

from pathlib import Path

from app.benchmark.benchmark_models import BenchmarkRow
from app.cube.low_vram_profiles import PROFILES, GenerationProfile
from app.system.gpu_detector import SystemDiagnostics
from app.utils.time_utils import utc_timestamp


def _markdown_table(rows: list[BenchmarkRow]) -> str:
    headers = [
        "Prompt",
        "Profile",
        "Success",
        "Seconds",
        "Peak VRAM GB",
        "Triangles",
        "Readiness",
        "Error",
    ]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.prompt.replace("|", "/"),
                    row.profile,
                    "yes" if row.success else "no",
                    f"{row.generation_time_seconds:.2f}",
                    "" if row.peak_vram_gb is None else f"{row.peak_vram_gb:.2f}",
                    "" if row.triangle_count is None else str(row.triangle_count),
                    "" if row.readiness_score is None else str(row.readiness_score),
                    row.error_message.replace("|", "/")[:120],
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def generate_technical_report(
    rows: list[BenchmarkRow],
    diagnostics: SystemDiagnostics,
    profiles: list[GenerationProfile],
    prompts: list[str],
    reports_dir: Path,
    cube_setup_note: str = "Cube 3D setup path is user-configured and weights are not redistributed by CubeLite Studio.",
) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"technical-report-{utc_timestamp()}.md"
    successes = sum(1 for row in rows if row.success)
    failures = len(rows) - successes
    avg_time = sum(row.generation_time_seconds for row in rows) / len(rows) if rows else 0
    peak_values = [row.peak_vram_gb for row in rows if row.peak_vram_gb is not None]
    max_peak = max(peak_values) if peak_values else None

    profile_lines = [
        f"- {profile.name}: target {profile.target_vram_gb} GB, resolution base {profile.resolution_base}, "
        f"fp16={profile.use_fp16}, cpu_offload={profile.enable_cpu_offload}, fast_inference={profile.fast_inference}"
        for profile in profiles
    ]
    prompt_lines = [f"- {prompt}" for prompt in prompts]
    report = f"""# CubeLite Studio: Low-VRAM Cube 3D Workflow Benchmark

## 1. Summary

CubeLite Studio is an independent local toolkit for testing Roblox Cube 3D workflows on consumer hardware. This report summarizes an experimental low-VRAM workflow, early benchmark results, mesh complexity, and heuristic Roblox-readiness checks. It is not official validation.

- Runs completed: {len(rows)}
- Successful runs: {successes}
- Failed runs: {failures}
- Average generation time: {avg_time:.2f} seconds
- Peak observed VRAM: {"" if max_peak is None else f"{max_peak:.2f} GB"}

## 2. Test Machine Specs

- OS: {diagnostics.os}
- CPU: {diagnostics.cpu}
- RAM: {diagnostics.ram_gb} GB
- Python: {diagnostics.python_version}
- PyTorch: {diagnostics.pytorch_version}
- CUDA available: {diagnostics.cuda_available}
- CUDA version: {diagnostics.cuda_version}
- GPU: {diagnostics.gpu_name}
- Total VRAM: {diagnostics.total_vram_gb} GB
- Free VRAM at check: {diagnostics.free_vram_gb} GB
- Recommended profile: {diagnostics.recommended_profile}

## 3. Cube 3D Setup

{cube_setup_note}

CubeLite Studio does not include or redistribute Cube 3D model weights. Users must obtain model files from official sources and follow the original license.

## 4. Profiles Tested

{chr(10).join(profile_lines)}

## 5. Benchmark Prompt Set

{chr(10).join(prompt_lines)}

## 6. Results Table

{_markdown_table(rows)}

## 7. VRAM Usage Comparison

Peak VRAM is recorded when NVIDIA telemetry is available through PyNVML or PyTorch CUDA memory APIs. Missing values mean VRAM telemetry was unavailable, not that no VRAM was used.

## 8. Generation Time Comparison

Generation time includes CubeLite orchestration and Cube process runtime. Dry-run rows are useful for validating the pipeline, but they are not model inference measurements.

## 9. Mesh Complexity Comparison

Triangle count and file size are measured from generated OBJ files where mesh loading succeeds. These values are practical indicators for Roblox import testing, not artistic quality scores.

## 10. Roblox Readiness Results

Readiness scores are heuristic and intentionally conservative. They flag high triangle counts, large files, unusual scale, missing geometry, and simplification failures.

## 11. What Worked

- Local dry-run workflow validates the complete pipeline without model files.
- Benchmark rows are preserved even when individual generations fail.
- Export packages include original mesh, optional optimized mesh, metadata, and Roblox import notes.

## 12. What Failed

Failures are captured in the results table. Typical failure classes include missing Cube 3D paths, missing weights, CUDA out-of-memory errors, subprocess failures, or missing OBJ outputs.

## 13. Limitations

- This project is independent and not affiliated with Roblox Corporation.
- Low-VRAM settings are workflow preferences unless the detected Cube command template maps them to supported Cube 3D options.
- Mesh readiness is a heuristic helper, not an official Roblox validation.
- Dry-run mode does not measure Cube 3D quality, speed, or VRAM usage.

## 14. Next Steps

- Add validated command templates for specific Cube 3D releases.
- Expand benchmark coverage across 6GB, 8GB, 12GB, 16GB, and 24GB GPUs.
- Add optional visual previews and turntable renders.
- Compare simplification quality across pymeshlab and other mesh tools.

## Potential Value for Roblox Creators

- Lowers the barrier for local experimentation.
- Gives creators clearer hardware expectations.
- Turns raw mesh generation into a Roblox import workflow.
- Helps identify where generation fails on consumer hardware.
- Creates benchmark data instead of vague guesses.
"""
    report_path.write_text(report, encoding="utf-8")
    return report_path
