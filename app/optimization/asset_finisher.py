from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.optimization.texture_generator import TextureResult, generate_texture_atlas
from app.optimization.uv_unwrapper import UVUnwrapResult, unwrap_obj_with_xatlas
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
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def finish_asset_for_roblox(
    input_obj: Path,
    output_dir: Path,
    prompt: str,
    texture_provider: str = "procedural",
) -> AssetFinishResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    texture_path = output_dir / "albedo.png"
    textured_obj = output_dir / "textured.obj"

    texture = generate_texture_atlas(prompt, texture_path, provider=texture_provider)
    if not texture.success:
        return _write_finish_report(
            output_dir,
            AssetFinishResult(False, None, None, None, None, None, texture.to_dict(), texture.error_message),
        )

    uv = unwrap_obj_with_xatlas(input_obj, textured_obj, texture_path)
    if not uv.success:
        return _write_finish_report(
            output_dir,
            AssetFinishResult(False, None, None, texture.output_path, None, uv.to_dict(), texture.to_dict(), uv.error_message),
        )

    return _write_finish_report(
        output_dir,
        AssetFinishResult(
            success=True,
            textured_obj_path=uv.output_obj_path,
            material_path=uv.output_mtl_path,
            texture_path=texture.output_path,
            report_path=None,
            uv_unwrap=uv.to_dict(),
            texture=texture.to_dict(),
        ),
    )


def _write_finish_report(output_dir: Path, result: AssetFinishResult) -> AssetFinishResult:
    report_path = output_dir / "finish_report.json"
    payload = result.to_dict()
    payload["timestamp"] = utc_iso()
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    result.report_path = str(report_path)
    return result

