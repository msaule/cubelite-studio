from __future__ import annotations

from dataclasses import asdict, dataclass
import math
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
    "crystal_core": (0.36, 0.95, 1.00),
    "crystal_edge": (0.12, 0.76, 0.90),
    "crystal_shadow": (0.08, 0.34, 0.58),
    "metal_dark": (0.16, 0.18, 0.22),
    "metal_mid": (0.36, 0.38, 0.43),
    "gold": (0.92, 0.62, 0.20),
    "gold_shadow": (0.58, 0.34, 0.10),
    "gem_green": (0.12, 0.95, 0.46),
    "grip_wrap": (0.09, 0.10, 0.13),
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

    _add_blade(builder, y0=0.04, y1=1.55)
    _add_blade_fuller(builder)
    _add_grip(builder)
    _add_guard(builder)
    _add_pommel(builder)
    _add_diamond(builder, "gem_green", center=(0.0, -0.025, 0.074), radius=0.060, depth=0.024)

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


def _add_blade(builder: _ObjBuilder, y0: float, y1: float) -> None:
    length = y1 - y0
    sections = [
        (y0, 0.155, 0.060),
        (y0 + length * 0.18, 0.132, 0.052),
        (y0 + length * 0.48, 0.092, 0.040),
        (y0 + length * 0.78, 0.052, 0.026),
        (y1, 0.0, 0.0),
    ]
    rings: list[list[int]] = []
    for y, width, thickness in sections:
        rings.append(
            [
                builder.add_vertex((-width, y, 0.0)),
                builder.add_vertex((-width * 0.38, y, thickness * 0.72)),
                builder.add_vertex((0.0, y, thickness)),
                builder.add_vertex((width * 0.38, y, thickness * 0.72)),
                builder.add_vertex((width, y, 0.0)),
                builder.add_vertex((width * 0.38, y, -thickness * 0.72)),
                builder.add_vertex((0.0, y, -thickness)),
                builder.add_vertex((-width * 0.38, y, -thickness * 0.72)),
            ]
        )
    for first, second in zip(rings, rings[1:]):
        for index in range(8):
            a = first[index]
            b = first[(index + 1) % 8]
            c = second[(index + 1) % 8]
            d = second[index]
            material = "crystal_core" if index in {1, 2, 5, 6} else ("crystal_edge" if index in {0, 3} else "crystal_shadow")
            builder.add_face(material, a, b, c)
            builder.add_face(material, a, c, d)


def _add_blade_fuller(builder: _ObjBuilder) -> None:
    _add_oriented_box_xy(builder, "crystal_edge", (-0.018, 0.16), (-0.010, 1.05), half_width=0.010, half_depth=0.066)
    _add_oriented_box_xy(builder, "crystal_edge", (0.018, 0.16), (0.010, 1.05), half_width=0.010, half_depth=0.066)


def _add_grip(builder: _ObjBuilder) -> None:
    _add_octagonal_prism(builder, "metal_dark", y0=-0.68, y1=0.025, radius_x=0.058, radius_z=0.044)
    for y in (-0.60, -0.47, -0.34, -0.21, -0.08):
        _add_box(builder, "gold_shadow", (-0.075, y - 0.018, -0.050), (0.075, y + 0.018, 0.050))
    _add_box(builder, "grip_wrap", (-0.047, -0.66, -0.052), (0.047, 0.01, 0.052))


def _add_guard(builder: _ObjBuilder) -> None:
    _add_box(builder, "metal_mid", (-0.130, -0.030, -0.070), (0.130, 0.060, 0.070))
    _add_oriented_box_xy(builder, "gold", (-0.55, -0.125), (-0.12, 0.030), half_width=0.055, half_depth=0.065)
    _add_oriented_box_xy(builder, "gold", (0.12, 0.030), (0.55, -0.125), half_width=0.055, half_depth=0.065)
    _add_diamond(builder, "gold_shadow", center=(-0.58, -0.135, 0.0), radius=0.052, depth=0.042)
    _add_diamond(builder, "gold_shadow", center=(0.58, -0.135, 0.0), radius=0.052, depth=0.042)


def _add_pommel(builder: _ObjBuilder) -> None:
    _add_box(builder, "gold", (-0.118, -0.835, -0.065), (0.118, -0.690, 0.065))
    _add_diamond(builder, "gold_shadow", center=(0.0, -0.940, 0.0), radius=0.092, depth=0.064)


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


def _add_oriented_box_xy(
    builder: _ObjBuilder,
    material: str,
    start: tuple[float, float],
    end: tuple[float, float],
    half_width: float,
    half_depth: float,
) -> None:
    sx, sy = start
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    length = max(math.hypot(dx, dy), 1e-6)
    px = -dy / length * half_width
    py = dx / length * half_width
    corners_2d = [
        (sx + px, sy + py),
        (ex + px, ey + py),
        (ex - px, ey - py),
        (sx - px, sy - py),
    ]
    front = [builder.add_vertex((x, y, half_depth)) for x, y in corners_2d]
    back = [builder.add_vertex((x, y, -half_depth)) for x, y in corners_2d]
    quads = [(front[0], front[1], front[2], front[3]), (back[3], back[2], back[1], back[0])]
    quads.extend((front[index], back[index], back[(index + 1) % 4], front[(index + 1) % 4]) for index in range(4))
    for a, b, c, d in quads:
        builder.add_face(material, a, b, c)
        builder.add_face(material, a, c, d)


def _add_octagonal_prism(builder: _ObjBuilder, material: str, y0: float, y1: float, radius_x: float, radius_z: float) -> None:
    rings: list[list[int]] = []
    for y in (y0, y1):
        ring = []
        for index in range(8):
            angle = (math.tau * index) / 8
            ring.append(builder.add_vertex((math.cos(angle) * radius_x, y, math.sin(angle) * radius_z)))
        rings.append(ring)
    for index in range(8):
        a = rings[0][index]
        b = rings[0][(index + 1) % 8]
        c = rings[1][(index + 1) % 8]
        d = rings[1][index]
        builder.add_face(material, a, b, c)
        builder.add_face(material, a, c, d)
    center_bottom = builder.add_vertex((0.0, y0, 0.0))
    center_top = builder.add_vertex((0.0, y1, 0.0))
    for index in range(8):
        builder.add_face(material, center_bottom, rings[0][(index + 1) % 8], rings[0][index])
        builder.add_face(material, center_top, rings[1][index], rings[1][(index + 1) % 8])


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
