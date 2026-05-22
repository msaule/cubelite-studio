from pathlib import Path

from app.benchmark.benchmark_runner import run_single_pipeline
from app.cube.low_vram_profiles import get_profile


def test_dry_run_creates_sample_mesh_and_export(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    exports = tmp_path / "exports"
    row, details = run_single_pipeline(
        prompt="low poly fantasy sword, single object",
        profile=get_profile("Benchmark Safe"),
        cube_repo_path=None,
        model_weights_path=None,
        outputs_dir=outputs,
        exports_dir=exports,
        dry_run=True,
        package_export=True,
    )
    assert row.success
    assert row.triangle_count == 12
    assert details["generation"]["dry_run"] is True
    export = details["export"]
    assert export["success"] is True
    assert Path(export["export_dir"]).exists()
