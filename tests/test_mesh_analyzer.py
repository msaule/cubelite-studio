from pathlib import Path

from app.optimization.mesh_analyzer import analyze_mesh


def test_missing_mesh_does_not_crash(tmp_path: Path) -> None:
    stats = analyze_mesh(tmp_path / "missing.obj")
    assert not stats.success
    assert "does not exist" in stats.error_message


def test_sample_obj_loads() -> None:
    stats = analyze_mesh(Path("sample_assets/sample_cube.obj"))
    assert stats.success
    assert stats.vertex_count == 8
    assert stats.triangle_count == 12


def test_invalid_obj_returns_useful_error(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.obj"
    invalid.write_text("this is not an obj\n", encoding="utf-8")
    stats = analyze_mesh(invalid)
    assert not stats.success
    assert stats.error_message
