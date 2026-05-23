from pathlib import Path

from app.cube.asset_styles import strengthen_prompt
from app.cube.cube_command_builder import build_cube_command
from app.cube.low_vram_profiles import get_profile
from app.cube.prompt_compiler import compile_asset_prompt, infer_asset_bbox


def test_sword_prompt_compiler_adds_asset_specific_structure() -> None:
    prompt = compile_asset_prompt("magic sword")

    assert "faceted cyan crystal blade" in prompt
    assert "gold crossguard" in prompt
    assert "no floating fragments" in prompt


def test_strengthen_prompt_keeps_sword_specific_terms() -> None:
    prompt = strengthen_prompt("magic sword", "Crystal Magic")

    assert "faceted cyan crystal blade" in prompt
    assert "stylized magical prop" in prompt


def test_sword_bbox_is_added_to_cubelite_command(tmp_path: Path) -> None:
    (tmp_path / "cubelite_cube_command.json").write_text(
        '{"command": ["python", "cubelite_low_vram_generate.py", "--prompt", "{prompt}", "--output-dir", "{output_dir}"]}',
        encoding="utf-8",
    )
    command = build_cube_command(
        prompt="magic sword",
        profile=get_profile("6GB Quality"),
        cube_repo_path=tmp_path,
        model_weights_path=tmp_path / "weights",
        output_dir=tmp_path / "outputs",
    )

    assert infer_asset_bbox("magic sword") == (0.34, 2.55, 0.18)
    assert "--bounding-box-xyz" in command.command
