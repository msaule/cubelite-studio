from pathlib import Path

from app.optimization.asset_finisher import finish_asset_for_roblox
from app.optimization.texture_analyzer import analyze_texture
from app.optimization.texture_generator import generate_texture_atlas, infer_material, normalize_texture_size
from app.optimization.uv_unwrapper import unwrap_obj_with_xatlas
from app.benchmark.texture_benchmark import run_texture_benchmark


def test_texture_generator_infers_prompt_material(tmp_path: Path) -> None:
    assert infer_material("low poly wooden crate") == "wood"
    result = generate_texture_atlas("low poly wooden crate", tmp_path / "albedo.png", size=256)

    assert result.success
    assert result.output_path
    assert Path(result.output_path).exists()
    stats = analyze_texture(Path(result.output_path))
    assert stats.success
    assert stats.width == 256
    assert stats.contrast_score is not None


def test_texture_size_normalization() -> None:
    assert normalize_texture_size(130) == 128


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


def test_texture_benchmark_records_provider_result(tmp_path: Path) -> None:
    result_path = run_texture_benchmark(
        input_obj=Path("sample_assets/sample_cube.obj"),
        prompt="low poly wooden crate",
        providers=["procedural"],
        output_dir=tmp_path,
        texture_size=256,
    )

    assert result_path.exists()
    text = result_path.read_text(encoding="utf-8")
    assert "procedural" in text
    assert "texture_contrast_score" in text
