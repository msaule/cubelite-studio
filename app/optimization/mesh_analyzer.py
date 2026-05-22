from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class MeshStats:
    success: bool
    path: str
    file_size_mb: float = 0.0
    vertex_count: int = 0
    face_count: int = 0
    triangle_count: int = 0
    bounding_box_dimensions: tuple[float, float, float] | None = None
    center_point: tuple[float, float, float] | None = None
    approximate_scale: float | None = None
    has_normals: bool = False
    has_materials: bool = False
    watertight: bool | None = None
    object_count: int | None = None
    warnings: list[str] = field(default_factory=list)
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _fallback_obj_parse(path: Path) -> MeshStats:
    text = path.read_text(encoding="utf-8", errors="replace")
    vertices = [line for line in text.splitlines() if line.startswith("v ")]
    faces = [line for line in text.splitlines() if line.startswith("f ")]
    normals = any(line.startswith("vn ") for line in text.splitlines())
    materials = any(line.startswith("mtllib ") or line.startswith("usemtl ") for line in text.splitlines())
    objects = [line for line in text.splitlines() if line.startswith("o ") or line.startswith("g ")]

    if not vertices or not faces:
        return MeshStats(
            success=False,
            path=str(path),
            file_size_mb=round(path.stat().st_size / (1024 * 1024), 3),
            vertex_count=len(vertices),
            face_count=len(faces),
            triangle_count=len(faces),
            has_normals=normals,
            has_materials=materials,
            object_count=len(objects) or None,
            error_message="OBJ file did not contain both vertices and faces.",
        )

    coords: list[tuple[float, float, float]] = []
    for line in vertices:
        try:
            _, x, y, z, *_ = line.split()
            coords.append((float(x), float(y), float(z)))
        except ValueError:
            continue
    bbox = None
    center = None
    scale = None
    if coords:
        xs, ys, zs = zip(*coords)
        bbox = (round(max(xs) - min(xs), 4), round(max(ys) - min(ys), 4), round(max(zs) - min(zs), 4))
        center = (round((max(xs) + min(xs)) / 2, 4), round((max(ys) + min(ys)) / 2, 4), round((max(zs) + min(zs)) / 2, 4))
        scale = round(max(bbox), 4)

    triangle_count = 0
    for line in faces:
        parts = line.split()[1:]
        triangle_count += max(1, len(parts) - 2)

    return MeshStats(
        success=True,
        path=str(path),
        file_size_mb=round(path.stat().st_size / (1024 * 1024), 3),
        vertex_count=len(vertices),
        face_count=len(faces),
        triangle_count=triangle_count,
        bounding_box_dimensions=bbox,
        center_point=center,
        approximate_scale=scale,
        has_normals=normals,
        has_materials=materials,
        watertight=None,
        object_count=len(objects) or None,
        warnings=["trimesh unavailable or failed; used lightweight OBJ parser."],
    )


def analyze_mesh(obj_path: Path) -> MeshStats:
    if not obj_path.exists():
        return MeshStats(success=False, path=str(obj_path), error_message="Mesh file does not exist.")
    if not obj_path.is_file():
        return MeshStats(success=False, path=str(obj_path), error_message="Mesh path is not a file.")

    try:
        import trimesh

        loaded = trimesh.load(str(obj_path), force="scene")
        geometries = list(getattr(loaded, "geometry", {}).values()) if hasattr(loaded, "geometry") else [loaded]
        meshes = [mesh for mesh in geometries if hasattr(mesh, "vertices") and hasattr(mesh, "faces")]
        if not meshes:
            return _fallback_obj_parse(obj_path)

        combined = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]
        if len(combined.vertices) == 0 or len(combined.faces) == 0:
            return MeshStats(
                success=False,
                path=str(obj_path),
                file_size_mb=round(obj_path.stat().st_size / (1024 * 1024), 3),
                error_message="Mesh loaded but contains no usable geometry.",
            )
        bounds = combined.bounds
        dims = tuple(round(float(value), 4) for value in combined.extents)
        center = tuple(round(float(value), 4) for value in combined.centroid)
        normals = "vn " in obj_path.read_text(encoding="utf-8", errors="ignore")
        materials = any(token in obj_path.read_text(encoding="utf-8", errors="ignore") for token in ("mtllib ", "usemtl "))
        return MeshStats(
            success=True,
            path=str(obj_path),
            file_size_mb=round(obj_path.stat().st_size / (1024 * 1024), 3),
            vertex_count=int(len(combined.vertices)),
            face_count=int(len(combined.faces)),
            triangle_count=int(len(combined.triangles)),
            bounding_box_dimensions=dims,
            center_point=center,
            approximate_scale=round(float(max(combined.extents)), 4),
            has_normals=normals,
            has_materials=materials,
            watertight=bool(combined.is_watertight),
            object_count=len(meshes),
            warnings=[] if bounds is not None else ["Bounds could not be calculated."],
        )
    except Exception as exc:
        try:
            return _fallback_obj_parse(obj_path)
        except Exception:
            return MeshStats(
                success=False,
                path=str(obj_path),
                file_size_mb=round(obj_path.stat().st_size / (1024 * 1024), 3),
                error_message=f"Mesh could not be loaded: {exc}",
            )
