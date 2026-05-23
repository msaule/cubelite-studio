from pathlib import Path

from app.optimization.mesh_analyzer import analyze_mesh
from app.optimization.prop_rebuilder import rebuild_prompt_proxy
from app.optimization.textured_renderer import render_material_inspection_plate


def test_prop_rebuilder_creates_clean_sword_proxy(tmp_path: Path) -> None:
    result = rebuild_prompt_proxy("low poly crystal sword", tmp_path / "proxy.obj")

    assert result.success
    assert result.asset_type == "fantasy_sword"
    assert result.output_obj_path and Path(result.output_obj_path).exists()
    assert result.output_mtl_path and Path(result.output_mtl_path).exists()

    stats = analyze_mesh(Path(result.output_obj_path))
    assert stats.success
    assert stats.triangle_count >= 20
    assert stats.has_materials

    render = render_material_inspection_plate(Path(result.output_obj_path), tmp_path / "proxy.png")
    assert render.success
    assert render.output_path and Path(render.output_path).exists()
