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
    assert (export_dir / "roblox_import_this.obj").exists()
    assert (export_dir / "metadata.json").exists()
    assert (export_dir / "roblox_import_notes.txt").exists()
    assert (export_dir / "asset_readme.md").exists()
    metadata = json.loads((export_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["dry_run"] is True
    assert metadata["readiness_score"] == readiness.score
    assert metadata["recommended_import_obj"] == "roblox_import_this.obj"
    readme = (export_dir / "asset_readme.md").read_text(encoding="utf-8")
    assert "roblox_import_this.obj" in readme
    assert "heuristic Roblox-readiness check" in readme


def test_export_packager_redacts_nested_finished_asset_paths(tmp_path: Path) -> None:
    original = Path("sample_assets/sample_cube.obj")
    stats = analyze_mesh(original)
    readiness = check_roblox_readiness(stats)
    private_path = tmp_path / "private" / "repair_proxy.obj"
    private_path.parent.mkdir()
    private_path.write_text(original.read_text(encoding="utf-8"), encoding="utf-8")

    result = create_export_package(
        prompt="simple sword",
        profile_name="Low VRAM",
        original_obj=original,
        exports_root=tmp_path / "exports",
        readiness=readiness,
        original_stats=stats,
        finished_asset={
            "repair_obj_path": str(private_path),
            "repair": {"output_obj_path": str(private_path), "asset_type": "fantasy_sword"},
            "texture_stats": {"path": str(tmp_path / "private" / "albedo.png"), "success": True},
        },
    )

    assert result.success
    metadata = json.loads(Path(result.metadata_path or "").read_text(encoding="utf-8"))
    assert metadata["repair"]["output_obj_path"] == "repair_proxy.obj"
    assert metadata["texture_quality"]["path"] == "albedo.png"
