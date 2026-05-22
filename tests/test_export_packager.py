import json
from pathlib import Path

from app.optimization.export_packager import create_export_package
from app.optimization.mesh_analyzer import analyze_mesh
from app.optimization.roblox_checker import check_roblox_readiness


def test_export_packager_creates_expected_files(tmp_path: Path) -> None:
    original = Path("sample_assets/sample_cube.obj")
    stats = analyze_mesh(original)
    readiness = check_roblox_readiness(stats)
    result = create_export_package(
        prompt="simple wooden crate, game asset",
        profile_name="Low VRAM",
        original_obj=original,
        exports_root=tmp_path,
        readiness=readiness,
        original_stats=stats,
        dry_run=True,
    )
    assert result.success
    export_dir = Path(result.export_dir or "")
    assert (export_dir / "original.obj").exists()
    assert (export_dir / "metadata.json").exists()
    assert (export_dir / "roblox_import_notes.txt").exists()
    metadata = json.loads((export_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["dry_run"] is True
    assert metadata["readiness_score"] == readiness.score
