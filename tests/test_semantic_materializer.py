from pathlib import Path

from app.optimization.semantic_materializer import materialize_obj_semantically
from app.optimization.textured_renderer import render_material_inspection_plate


def test_semantic_materializer_writes_obj_mtl_and_preview(tmp_path: Path) -> None:
    result = materialize_obj_semantically(
        Path("sample_assets/sample_cube.obj"),
        tmp_path / "semantic_material.obj",
        "low poly wooden crate with darker plank braces",
    )

    assert result.success
    assert result.output_obj_path and Path(result.output_obj_path).exists()
    assert result.output_mtl_path and Path(result.output_mtl_path).exists()
    obj_text = Path(result.output_obj_path).read_text(encoding="utf-8")
    mtl_text = Path(result.output_mtl_path).read_text(encoding="utf-8")
    assert "usemtl wood" in obj_text
    assert "Kd " in mtl_text

    render = render_material_inspection_plate(Path(result.output_obj_path), tmp_path / "preview.png")
    assert render.success
    assert render.output_path and Path(render.output_path).exists()


def test_semantic_materializer_marks_crystal_sword(tmp_path: Path) -> None:
    sword = tmp_path / "sword.obj"
    sword.write_text(
        "\n".join(
            [
                "v -0.05 -1.0 0.0",
                "v 0.05 -1.0 0.0",
                "v 0.02 1.0 0.0",
                "v -0.02 1.0 0.0",
                "v 0.0 0.0 0.08",
                "f 1 2 5",
                "f 2 3 5",
                "f 3 4 5",
                "f 4 1 5",
            ]
        ),
        encoding="utf-8",
    )

    result = materialize_obj_semantically(
        sword,
        tmp_path / "semantic_sword.obj",
        "purple crystal blade fantasy sword with green gem accents",
    )

    assert result.success
    obj_text = Path(result.output_obj_path).read_text(encoding="utf-8")
    assert "crystal" in obj_text
