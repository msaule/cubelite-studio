from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.optimization.texture_analyzer import analyze_texture
from app.optimization.texture_generator import generate_material_pack
from app.optimization.uv_unwrapper import unwrap_obj_with_xatlas
from app.optimization.semantic_materializer import materialize_obj_semantically
from app.optimization.textured_renderer import render_material_inspection_plate
from app.optimization.prop_rebuilder import rebuild_prompt_proxy
from app.utils.time_utils import utc_iso


@dataclass
class AssetFinishResult:
    success: bool
    textured_obj_path: str | None
    material_path: str | None
    texture_path: str | None
    report_path: str | None
    uv_unwrap: dict[str, object] | None
    texture: dict[str, object] | None
    normal_path: str | None = None
    roughness_path: str | None = None
    metallic_path: str | None = None
    semantic_obj_path: str | None = None
    semantic_material_path: str | None = None
    material_preview_path: str | None = None
    semantic_material: dict[str, object] | None = None
    repair_obj_path: str | None = None
    repair_material_path: str | None = None
    repair_preview_path: str | None = None
    repair: dict[str, object] | None = None
    texture_stats: dict[str, object] | None = None
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def finish_asset_for_roblox(
    input_obj: Path,
    output_dir: Path,
    prompt: str,
    texture_provider: str = "procedural",
    texture_model_id: str | None = None,
    texture_steps: int = 8,
    texture_size: int = 1024,
    texture_seed: int = 0,
) -> AssetFinishResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    texture_path = output_dir / "albedo.png"
    textured_obj = output_dir / "textured.obj"

    texture = generate_material_pack(
        prompt,
        output_dir,
        size=texture_size,
        provider=texture_provider,
        model_id=texture_model_id,
        steps=texture_steps,
        seed=texture_seed,
    )
    if not texture.success:
        return _write_finish_report(
            output_dir,
            AssetFinishResult(
                success=False,
                textured_obj_path=None,
                material_path=None,
                texture_path=None,
                report_path=None,
                uv_unwrap=None,
                texture=texture.to_dict(),
                error_message=texture.error_message,
            ),
        )
    texture_path = Path(texture.map_paths.get("albedo", texture.output_path or texture_path))
    normal_path = Path(texture.map_paths["normal"]) if texture.map_paths.get("normal") else None
    roughness_path = Path(texture.map_paths["roughness"]) if texture.map_paths.get("roughness") else None
    metallic_path = Path(texture.map_paths["metallic"]) if texture.map_paths.get("metallic") else None

    uv = unwrap_obj_with_xatlas(
        input_obj,
        textured_obj,
        texture_path,
        normal_path=normal_path,
        roughness_path=roughness_path,
        metallic_path=metallic_path,
    )
    texture_stats = analyze_texture(texture_path).to_dict()
    if not uv.success:
        return _write_finish_report(
            output_dir,
            AssetFinishResult(
                success=False,
                textured_obj_path=None,
                material_path=None,
                texture_path=str(texture_path),
                report_path=None,
                uv_unwrap=uv.to_dict(),
                texture=texture.to_dict(),
                normal_path=str(normal_path) if normal_path else None,
                roughness_path=str(roughness_path) if roughness_path else None,
                metallic_path=str(metallic_path) if metallic_path else None,
                texture_stats=texture_stats,
                error_message=uv.error_message,
            ),
        )

    semantic = materialize_obj_semantically(input_obj, output_dir / "semantic_material.obj", prompt)
    material_preview_path = None
    if semantic.success and semantic.output_obj_path:
        preview = render_material_inspection_plate(
            Path(semantic.output_obj_path),
            output_dir / "semantic_material_preview.png",
            "Semantic material inspection",
            show_edges=False,
        )
        material_preview_path = preview.output_path if preview.success else None

    repair = rebuild_prompt_proxy(prompt, output_dir / "repair_proxy.obj")
    repair_preview_path = None
    if repair.success and repair.output_obj_path:
        repair_preview = render_material_inspection_plate(
            Path(repair.output_obj_path),
            output_dir / "repair_proxy_preview.png",
            "Procedural repair proxy",
            show_edges=True,
        )
        repair_preview_path = repair_preview.output_path if repair_preview.success else None

    return _write_finish_report(
        output_dir,
        AssetFinishResult(
            success=True,
            textured_obj_path=uv.output_obj_path,
            material_path=uv.output_mtl_path,
            texture_path=str(texture_path),
            normal_path=str(normal_path) if normal_path else None,
            roughness_path=str(roughness_path) if roughness_path else None,
            metallic_path=str(metallic_path) if metallic_path else None,
            semantic_obj_path=semantic.output_obj_path,
            semantic_material_path=semantic.output_mtl_path,
            material_preview_path=material_preview_path,
            semantic_material=semantic.to_dict(),
            repair_obj_path=repair.output_obj_path,
            repair_material_path=repair.output_mtl_path,
            repair_preview_path=repair_preview_path,
            repair=repair.to_dict(),
            report_path=None,
            uv_unwrap=uv.to_dict(),
            texture=texture.to_dict(),
            texture_stats=texture_stats,
        ),
    )


def _write_finish_report(output_dir: Path, result: AssetFinishResult) -> AssetFinishResult:
    report_path = output_dir / "finish_report.json"
    result.report_path = str(report_path)
    payload = result.to_dict()
    payload["timestamp"] = utc_iso()
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return result
