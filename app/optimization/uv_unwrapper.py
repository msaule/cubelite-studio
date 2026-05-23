from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class UVUnwrapResult:
    success: bool
    output_obj_path: str | None
    output_mtl_path: str | None
    texture_path: str | None
    vertex_count: int = 0
    face_count: int = 0
    uv_count: int = 0
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def unwrap_obj_with_xatlas(
    input_obj: Path,
    output_obj: Path,
    texture_path: Path,
    material_name: str = "cubelite_material",
    normal_path: Path | None = None,
    roughness_path: Path | None = None,
    metallic_path: Path | None = None,
) -> UVUnwrapResult:
    if not input_obj.exists():
        return UVUnwrapResult(False, None, None, None, error_message="Input OBJ does not exist.")

    try:
        import numpy as np
        import trimesh
        import xatlas
    except Exception as exc:
        return UVUnwrapResult(
            False,
            None,
            None,
            None,
            error_message=f"UV unwrap dependencies are unavailable: {exc}. Install xatlas and trimesh.",
        )

    try:
        loaded = trimesh.load(str(input_obj), force="scene")
        geometries = list(getattr(loaded, "geometry", {}).values()) if hasattr(loaded, "geometry") else [loaded]
        meshes = [mesh for mesh in geometries if hasattr(mesh, "vertices") and hasattr(mesh, "faces") and len(mesh.faces) > 0]
        if not meshes:
            return UVUnwrapResult(False, None, None, None, error_message="Mesh has no usable faces.")
        mesh = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]

        vertices = np.asarray(mesh.vertices, dtype=np.float32)
        faces = np.asarray(mesh.faces, dtype=np.uint32)
        vmapping, indices, uvs = xatlas.parametrize(vertices, faces)
        remapped_vertices = vertices[vmapping]

        output_obj.parent.mkdir(parents=True, exist_ok=True)
        output_mtl = output_obj.with_suffix(".mtl")
        _write_textured_obj(output_obj, output_mtl.name, material_name, remapped_vertices, indices, uvs)
        _write_mtl(
            output_mtl,
            material_name,
            texture_path.name,
            normal_path.name if normal_path else None,
            roughness_path.name if roughness_path else None,
            metallic_path.name if metallic_path else None,
        )

        return UVUnwrapResult(
            success=True,
            output_obj_path=str(output_obj),
            output_mtl_path=str(output_mtl),
            texture_path=str(texture_path),
            vertex_count=int(len(remapped_vertices)),
            face_count=int(len(indices)),
            uv_count=int(len(uvs)),
        )
    except Exception as exc:
        return UVUnwrapResult(False, None, None, None, error_message=f"UV unwrap failed: {exc}")


def _write_textured_obj(
    output_obj: Path,
    mtl_name: str,
    material_name: str,
    vertices,
    indices,
    uvs,
) -> None:
    with output_obj.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# CubeLite Studio textured OBJ\n")
        handle.write(f"mtllib {mtl_name}\n")
        handle.write(f"usemtl {material_name}\n")
        for vertex in vertices:
            handle.write(f"v {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}\n")
        for uv in uvs:
            handle.write(f"vt {uv[0]:.6f} {1.0 - uv[1]:.6f}\n")
        for face in indices:
            a, b, c = (int(face[0]) + 1, int(face[1]) + 1, int(face[2]) + 1)
            handle.write(f"f {a}/{a} {b}/{b} {c}/{c}\n")


def _write_mtl(
    output_mtl: Path,
    material_name: str,
    texture_name: str,
    normal_name: str | None = None,
    roughness_name: str | None = None,
    metallic_name: str | None = None,
) -> None:
    lines = [
        "# CubeLite Studio material",
        f"newmtl {material_name}",
        "Ka 1.000 1.000 1.000",
        "Kd 1.000 1.000 1.000",
        "Ks 0.000 0.000 0.000",
        "Ns 16.000",
        f"map_Kd {texture_name}",
    ]
    if normal_name:
        lines.append(f"map_Bump {normal_name}")
    if roughness_name:
        lines.append(f"# roughness_map {roughness_name}")
    if metallic_name:
        lines.append(f"# metallic_map {metallic_name}")
    lines.append("")
    output_mtl.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )
