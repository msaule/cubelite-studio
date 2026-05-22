from pathlib import Path

from app.optimization.mesh_renderer import render_mesh_inspection_plate, render_mesh_preview


def test_mesh_renderer_creates_preview(tmp_path: Path) -> None:
    result = render_mesh_preview(Path("sample_assets/sample_cube.obj"), tmp_path / "preview.png")
    assert result.success
    assert result.output_path
    assert Path(result.output_path).exists()


def test_mesh_renderer_creates_inspection_plate(tmp_path: Path) -> None:
    result = render_mesh_inspection_plate(Path("sample_assets/sample_cube.obj"), tmp_path / "plate.png")
    assert result.success
    assert result.output_path
    assert Path(result.output_path).exists()
