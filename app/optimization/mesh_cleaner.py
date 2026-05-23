from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import shutil


@dataclass
class MeshCleanupResult:
    success: bool
    input_faces: int
    output_faces: int
    removed_components: int
    kept_components: int
    output_path: str | None
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def remove_small_components(
    input_obj: Path,
    output_obj: Path,
    min_face_ratio: float = 0.03,
    min_faces: int = 64,
) -> MeshCleanupResult:
    if not input_obj.exists():
        return MeshCleanupResult(False, 0, 0, 0, 0, None, "Input OBJ does not exist.")

    try:
        import trimesh
    except Exception as exc:
        return MeshCleanupResult(False, 0, 0, 0, 0, None, f"trimesh is required for mesh cleanup: {exc}")

    try:
        mesh = trimesh.load(input_obj, force="mesh", process=False)
        mesh.merge_vertices()
        if mesh.is_empty or len(mesh.faces) == 0:
            return MeshCleanupResult(False, 0, 0, 0, 0, None, "Input OBJ has no faces to clean.")
        components = list(mesh.split(only_watertight=False))
        if len(components) <= 1:
            output_obj.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(input_obj, output_obj)
            return MeshCleanupResult(True, int(len(mesh.faces)), int(len(mesh.faces)), 0, 1, str(output_obj))

        largest_faces = max(len(component.faces) for component in components)
        threshold = max(int(largest_faces * min_face_ratio), int(min_faces))
        kept = [component for component in components if len(component.faces) >= threshold]
        if not kept:
            kept = [max(components, key=lambda component: len(component.faces))]

        output_mesh = trimesh.util.concatenate(kept) if len(kept) > 1 else kept[0]
        output_obj.parent.mkdir(parents=True, exist_ok=True)
        output_mesh.export(output_obj)
        removed = len(components) - len(kept)
        return MeshCleanupResult(
            True,
            int(len(mesh.faces)),
            int(len(output_mesh.faces)),
            removed,
            len(kept),
            str(output_obj),
        )
    except Exception as exc:
        return MeshCleanupResult(False, 0, 0, 0, 0, None, f"Mesh cleanup failed: {exc}")
