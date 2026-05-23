from pathlib import Path

from app.optimization.asset_finisher import finish_asset_for_roblox
from app.optimization.texture_generator import generate_texture_atlas, infer_material
from app.optimization.uv_unwrapper import unwrap_obj_with_xatlas


def test_texture_generator_infers_prompt_material(tmp_path: Path) -> None:
    assert infer_material("low poly wooden crate") == "wood"
    result = generate_texture_atlas("low poly wooden crate", tmp_path / "albedo.png", size=256)

    assert result.success
    assert result.output_path
    assert Path(result.output_path).exists()


def test_uv_unwrapper_writes_textured_obj(tmp_path: Path) -> None:
    texture = tmp_path / "albedo.png"
    texture.write_bytes(b"fake")
    result = unwrap_obj_with_xatlas(
        Path("sample_assets/sample_cube.obj"),
        tmp_path / "textured.obj",
        texture,
    )

    assert result.success
    assert result.output_obj_path
    obj_text = Path(result.output_obj_path).read_text(encoding="utf-8")
    assert "mtllib textured.mtl" in obj_text
    assert "vt " in obj_text
    assert "/" in obj_text
    assert result.output_mtl_path
    assert Path(result.output_mtl_path).exists()


def test_asset_finisher_creates_obj_mtl_texture_and_report(tmp_path: Path) -> None:
    result = finish_asset_for_roblox(
        Path("sample_assets/sample_cube.obj"),
        tmp_path,
        "low poly wooden crate",
    )

    assert result.success
    assert result.textured_obj_path and Path(result.textured_obj_path).exists()
    assert result.material_path and Path(result.material_path).exists()
    assert result.texture_path and Path(result.texture_path).exists()
    assert result.report_path and Path(result.report_path).exists()

