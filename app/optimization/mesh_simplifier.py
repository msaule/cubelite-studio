from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import shutil

from app.optimization.mesh_analyzer import analyze_mesh


@dataclass
class SimplificationResult:
    success: bool
    input_faces: int
    output_faces: int
    target_faces: int
    reduction_percent: float
    output_path: str | None
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def simplify_mesh(input_obj: Path, output_obj: Path, target_faces: int) -> SimplificationResult:
    input_stats = analyze_mesh(input_obj)
    if not input_stats.success:
        return SimplificationResult(False, 0, 0, target_faces, 0.0, None, input_stats.error_message)

    try:
        import pymeshlab
    except Exception:
        output_obj.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(input_obj, output_obj)
        return SimplificationResult(
            success=False,
            input_faces=input_stats.triangle_count,
            output_faces=input_stats.triangle_count,
            target_faces=target_faces,
            reduction_percent=0.0,
            output_path=str(output_obj),
            error_message="pymeshlab is not installed. Install it with 'pip install pymeshlab' to enable mesh simplification.",
        )

    try:
        output_obj.parent.mkdir(parents=True, exist_ok=True)
        meshset = pymeshlab.MeshSet()
        meshset.load_new_mesh(str(input_obj))
        meshset.meshing_decimation_quadric_edge_collapse(targetfacenum=int(target_faces), preservenormal=True)
        meshset.save_current_mesh(str(output_obj))
        output_stats = analyze_mesh(output_obj)
        reduction = 0.0
        if input_stats.triangle_count:
            reduction = round((1 - (output_stats.triangle_count / input_stats.triangle_count)) * 100, 2)
        return SimplificationResult(
            success=output_stats.success,
            input_faces=input_stats.triangle_count,
            output_faces=output_stats.triangle_count,
            target_faces=target_faces,
            reduction_percent=reduction,
            output_path=str(output_obj) if output_stats.success else None,
            error_message="" if output_stats.success else output_stats.error_message,
        )
    except Exception as exc:
        return SimplificationResult(
            success=False,
            input_faces=input_stats.triangle_count,
            output_faces=input_stats.triangle_count,
            target_faces=target_faces,
            reduction_percent=0.0,
            output_path=None,
            error_message=f"Mesh simplification failed: {exc}",
        )
