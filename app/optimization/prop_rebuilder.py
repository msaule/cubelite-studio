from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class PropRebuildResult:
    success: bool
    output_obj_path: str | None
    output_mtl_path: str | None
    asset_type: str = ""
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


MATERIALS = {
    "crystal_blade": (0.22, 0.88, 0.96),
    "crystal_shadow": (0.12, 0.46, 0.70),
    "metal_dark": (0.22, 0.24, 0.28),
    "gold": (0.92, 0.62, 0.20),
    "gem_green": (0.15, 0.92, 0.42),
    "wood": (0.55, 0.31, 0.13),
}


def rebuild_prompt_proxy(prompt: str, output_obj: Path) -> PropRebuildResult:
    lower = prompt.lower()
    if "sword" in lower:
        return rebuild_fantasy_sword(output_obj)
    return PropRebuildResult(False, None, None, error_message="No procedural repair template exists for this prompt yet.")


def rebuild_fantasy_sword(output_obj: Path) -> PropRebuildResult:
    output_obj.parent.mkdir(parents=True, exist_ok=True)
    output_mtl = output_obj.with_suffix(".mtl")
    builder = _ObjBuilder()

    _add_blade(builder, y0=0.08, y1=1.42, width0=0.105, width1=0.035, thickness0=0.040, thickness1=0.014)
    _add_box(builder, "metal_dark", (-0.075, -0.72, -0.040), (0.075, 0.08, 0.040))
    _add_box(builder, "gold", (-0.50, -0.06, -0.060), (0.50, 0.045, 0.060))
    _add_box(builder, "gold", (-0.13, -0.84, -0.060), (0.13, -0.70, 0.060))
    _add_diamond(builder, "gem_green", center=(0.0, -0.03, 0.066), radius=0.055, depth=0.018)
    _add_diamond(builder, "gold", center=(0.0, -0.94, 0.0), radius=0.085, depth=0.055)

    _write_mtl(output_mtl)
    _write_obj(output_obj, output_mtl.name, builder)
    return PropRebuildResult(True, str(output_obj), str(output_mtl), "fantasy_sword")


class _ObjBuilder:
    def __init__(self) -> None:
        self.vertices: list[tuple[float, float, float]] = []
        self.faces: list[tuple[str, tuple[int, int, int]]] = []

    def add_vertex(self, vertex: tuple[float, float, float]) -> int:
        self.vertices.append(vertex)
        return len(self.vertices)

    def add_face(self, material: str, a: int, b: int, c: int) -> None:
        self.faces.append((material, (a, b, c)))


def _add_blade(builder: _ObjBuilder, y0: float, y1: float, width0: float, width1: float, thickness0: float, thickness1: float) -> None:
    ym = y0 + (y1 - y0) * 0.68
    sections = [
        (y0, width0, thickness0),
        (ym, width1 * 1.5, thickness1 * 1.6),
        (y1, 0.0, 0.0),
    ]
    rings: list[list[int]] = []
    for y, width, thickness in sections:
        rings.append(
            [
                builder.add_vertex((-width, y, 0.0)),
                builder.add_vertex((0.0, y, thickness)),
                builder.add_vertex((width, y, 0.0)),
                builder.add_vertex((0.0, y, -thickness)),
            ]
        )
    for first, second in zip(rings, rings[1:]):
        for index in range(4):
            a = first[index]
            b = first[(index + 1) % 4]
            c = second[(index + 1) % 4]
            d = second[index]
            material = "crystal_blade" if index in {0, 1} else "crystal_shadow"
            builder.add_face(material, a, b, c)
            builder.add_face(material, a, c, d)


def _add_box(builder: _ObjBuilder, material: str, mins: tuple[float, float, float], maxs: tuple[float, float, float]) -> None:
    x0, y0, z0 = mins
    x1, y1, z1 = maxs
    verts = [
        builder.add_vertex((x0, y0, z0)),
        builder.add_vertex((x1, y0, z0)),
        builder.add_vertex((x1, y1, z0)),
        builder.add_vertex((x0, y1, z0)),
        builder.add_vertex((x0, y0, z1)),
        builder.add_vertex((x1, y0, z1)),
        builder.add_vertex((x1, y1, z1)),
        builder.add_vertex((x0, y1, z1)),
    ]
    quads = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (3, 2, 6, 7), (0, 3, 7, 4), (1, 5, 6, 2)]
    for a, b, c, d in quads:
        builder.add_face(material, verts[a], verts[b], verts[c])
        builder.add_face(material, verts[a], verts[c], verts[d])


def _add_diamond(builder: _ObjBuilder, material: str, center: tuple[float, float, float], radius: float, depth: float) -> None:
    x, y, z = center
    top = builder.add_vertex((x, y + radius, z))
    right = builder.add_vertex((x + radius, y, z))
    bottom = builder.add_vertex((x, y - radius, z))
    left = builder.add_vertex((x - radius, y, z))
    front = builder.add_vertex((x, y, z + depth))
    back = builder.add_vertex((x, y, z - depth))
    for apex in (front, back):
        builder.add_face(material, top, right, apex)
        builder.add_face(material, right, bottom, apex)
        builder.add_face(material, bottom, left, apex)
        builder.add_face(material, left, top, apex)


def _write_mtl(output_mtl: Path) -> None:
    lines = ["# CubeLite procedural repair materials"]
    for name, color in MATERIALS.items():
        r, g, b = color
        lines.extend([f"newmtl {name}", f"Kd {r:.4f} {g:.4f} {b:.4f}", "Ka 0.7000 0.7000 0.7000", "Ks 0.1000 0.1000 0.1000", "Ns 32.0000", ""])
    output_mtl.write_text("\n".join(lines), encoding="utf-8")


def _write_obj(output_obj: Path, mtl_name: str, builder: _ObjBuilder) -> None:
    lines = ["# CubeLite procedural repair mesh", f"mtllib {mtl_name}"]
    for vertex in builder.vertices:
        lines.append(f"v {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}")
    current = ""
    for material, (a, b, c) in builder.faces:
        if material != current:
            lines.append(f"usemtl {material}")
            current = material
        lines.append(f"f {a} {b} {c}")
    output_obj.write_text("\n".join(lines) + "\n", encoding="utf-8")
