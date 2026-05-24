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
    "crystal_highlight": (0.72, 1.00, 1.00),
    "crystal_edge": (0.12, 0.76, 0.90),
    "crystal_shadow": (0.08, 0.34, 0.58),
    "crystal_deep": (0.06, 0.20, 0.46),
    "metal_dark": (0.16, 0.18, 0.22),
    "metal_mid": (0.36, 0.38, 0.43),
    "metal_edge": (0.58, 0.61, 0.68),
    "gold": (0.92, 0.62, 0.20),
    "gold_light": (1.00, 0.78, 0.34),
    "gold_shadow": (0.58, 0.34, 0.10),
    "gem_green": (0.12, 0.95, 0.46),
    "gem_dark": (0.04, 0.38, 0.20),
    "grip_wrap": (0.09, 0.10, 0.13),
    "leather": (0.20, 0.11, 0.06),
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

    _add_fantasy_blade(builder)
    _add_blade_fuller(builder)
    _add_blade_socket(builder)
    _add_grip(builder)
    _add_guard(builder)
    _add_pommel(builder)
    _add_diamond(builder, "gem_green", center=(0.0, -0.025, 0.074), radius=0.060, depth=0.024)
    _add_diamond(builder, "gem_dark", center=(0.0, -0.025, -0.074), radius=0.048, depth=0.018)

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

    def add_quad(self, material: str, a: int, b: int, c: int, d: int) -> None:
        self.add_face(material, a, b, c)
        self.add_face(material, a, c, d)


def _add_fantasy_blade(builder: _ObjBuilder) -> None:
    outline = [
        (-0.205, 0.030),
        (-0.285, 0.170),
        (-0.185, 0.305),
        (-0.142, 0.760),
        (-0.096, 1.185),
        (-0.050, 1.500),
        (0.000, 1.655),
        (0.050, 1.500),
        (0.096, 1.185),
        (0.142, 0.760),
        (0.185, 0.305),
        (0.285, 0.170),
        (0.205, 0.030),
    ]
    _add_extruded_polygon(builder, "crystal_core", outline, half_depth=0.055)
    inner_left = [
        (-0.050, 0.130),
        (-0.150, 0.290),
        (-0.110, 0.780),
        (-0.060, 1.260),
        (-0.015, 1.480),
        (0.000, 1.535),
        (0.000, 0.095),
    ]
    inner_right = [(-x, y) for x, y in reversed(inner_left)]
    _add_surface_polygon(builder, "crystal_highlight", inner_left, z=0.061)
    _add_surface_polygon(builder, "crystal_edge", inner_right, z=0.062)
    _add_surface_polygon(builder, "crystal_shadow", inner_left, z=-0.061, reverse=True)
    _add_surface_polygon(builder, "crystal_deep", inner_right, z=-0.062, reverse=True)
    _add_raised_ridge(builder, y0=0.120, y1=1.520, z=0.072)


def _add_blade_fuller(builder: _ObjBuilder) -> None:
    _add_oriented_box_xy(builder, "crystal_deep", (-0.032, 0.19), (-0.012, 1.12), half_width=0.007, half_depth=0.071)
    _add_oriented_box_xy(builder, "crystal_deep", (0.032, 0.19), (0.012, 1.12), half_width=0.007, half_depth=0.071)
    _add_oriented_box_xy(builder, "crystal_highlight", (0.000, 0.20), (0.000, 1.34), half_width=0.006, half_depth=0.076)
    for y in (0.36, 0.62, 0.88, 1.12):
        _add_diamond(builder, "crystal_edge", center=(0.0, y, 0.078), radius=0.026, depth=0.007)


def _add_blade_socket(builder: _ObjBuilder) -> None:
    _add_box(builder, "metal_edge", (-0.150, -0.010, -0.075), (0.150, 0.095, 0.075))
    _add_box(builder, "gold_shadow", (-0.115, -0.045, -0.080), (0.115, 0.005, 0.080))
    _add_diamond(builder, "gem_green", center=(0.0, 0.050, 0.086), radius=0.048, depth=0.018)


def _add_grip(builder: _ObjBuilder) -> None:
    _add_octagonal_prism(builder, "leather", y0=-0.70, y1=0.030, radius_x=0.066, radius_z=0.050, sides=12)
    for index, y in enumerate((-0.62, -0.51, -0.40, -0.29, -0.18, -0.07)):
        slant = 0.045 if index % 2 == 0 else -0.045
        _add_oriented_box_xy(builder, "gold_shadow", (-0.080, y - 0.025), (0.080, y + slant), half_width=0.018, half_depth=0.058)
    _add_octagonal_prism(builder, "grip_wrap", y0=-0.72, y1=-0.69, radius_x=0.084, radius_z=0.062, sides=12)
    _add_octagonal_prism(builder, "grip_wrap", y0=0.010, y1=0.045, radius_x=0.084, radius_z=0.062, sides=12)


def _add_guard(builder: _ObjBuilder) -> None:
    _add_box(builder, "metal_mid", (-0.175, -0.060, -0.082), (0.175, 0.055, 0.082))
    _add_oriented_box_xy(builder, "gold", (-0.62, -0.155), (-0.12, 0.035), half_width=0.065, half_depth=0.072)
    _add_oriented_box_xy(builder, "gold", (0.12, 0.035), (0.62, -0.155), half_width=0.065, half_depth=0.072)
    _add_oriented_box_xy(builder, "gold_light", (-0.52, -0.105), (-0.17, 0.025), half_width=0.020, half_depth=0.078)
    _add_oriented_box_xy(builder, "gold_light", (0.17, 0.025), (0.52, -0.105), half_width=0.020, half_depth=0.078)
    _add_diamond(builder, "gold_shadow", center=(-0.66, -0.170, 0.0), radius=0.064, depth=0.050)
    _add_diamond(builder, "gold_shadow", center=(0.66, -0.170, 0.0), radius=0.064, depth=0.050)
    _add_diamond(builder, "gem_green", center=(-0.37, -0.070, 0.082), radius=0.034, depth=0.012)
    _add_diamond(builder, "gem_green", center=(0.37, -0.070, 0.082), radius=0.034, depth=0.012)


def _add_pommel(builder: _ObjBuilder) -> None:
    _add_octagonal_prism(builder, "gold", y0=-0.860, y1=-0.700, radius_x=0.112, radius_z=0.072, sides=8)
    _add_octagonal_prism(builder, "gold_light", y0=-0.805, y1=-0.755, radius_x=0.140, radius_z=0.082, sides=8)
    _add_diamond(builder, "gem_green", center=(0.0, -0.780, 0.088), radius=0.040, depth=0.016)
    _add_diamond(builder, "gold_shadow", center=(0.0, -0.980, 0.0), radius=0.105, depth=0.070)


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
        builder.add_quad(material, verts[a], verts[b], verts[c], verts[d])


def _add_extruded_polygon(builder: _ObjBuilder, material: str, outline: list[tuple[float, float]], half_depth: float) -> None:
    front = [builder.add_vertex((x, y, half_depth)) for x, y in outline]
    back = [builder.add_vertex((x, y, -half_depth)) for x, y in outline]
    center_x = sum(x for x, _ in outline) / len(outline)
    center_y = sum(y for _, y in outline) / len(outline)
    front_center = builder.add_vertex((center_x, center_y, half_depth))
    back_center = builder.add_vertex((center_x, center_y, -half_depth))
    count = len(outline)
    for index in range(count):
        next_index = (index + 1) % count
        edge_material = "crystal_edge" if index in {0, 1, 10, 11, 12} else ("crystal_shadow" if index in {4, 5, 6, 7} else material)
        builder.add_face("crystal_highlight" if index < count // 2 else material, front_center, front[index], front[next_index])
        builder.add_face("crystal_deep" if index < count // 2 else "crystal_shadow", back_center, back[next_index], back[index])
        builder.add_quad(edge_material, front[index], back[index], back[next_index], front[next_index])


def _add_surface_polygon(builder: _ObjBuilder, material: str, outline: list[tuple[float, float]], z: float, reverse: bool = False) -> None:
    vertices = [builder.add_vertex((x, y, z)) for x, y in outline]
    center_x = sum(x for x, _ in outline) / len(outline)
    center_y = sum(y for _, y in outline) / len(outline)
    center = builder.add_vertex((center_x, center_y, z))
    indices = range(len(vertices))
    if reverse:
        indices = reversed(range(len(vertices)))
    ordered = list(indices)
    for offset, index in enumerate(ordered):
        next_index = ordered[(offset + 1) % len(ordered)]
        builder.add_face(material, center, vertices[index], vertices[next_index])


def _add_raised_ridge(builder: _ObjBuilder, y0: float, y1: float, z: float) -> None:
    points = [
        builder.add_vertex((-0.014, y0, z)),
        builder.add_vertex((0.000, y0 + 0.060, z + 0.022)),
        builder.add_vertex((0.014, y0, z)),
        builder.add_vertex((-0.010, y1, z)),
        builder.add_vertex((0.000, y1 + 0.040, z + 0.016)),
        builder.add_vertex((0.010, y1, z)),
    ]
    builder.add_quad("crystal_highlight", points[0], points[1], points[4], points[3])
    builder.add_quad("crystal_edge", points[1], points[2], points[5], points[4])
    builder.add_quad("crystal_deep", points[0], points[3], points[5], points[2])


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
        builder.add_quad(material, a, b, c, d)


def _add_octagonal_prism(builder: _ObjBuilder, material: str, y0: float, y1: float, radius_x: float, radius_z: float, sides: int = 8) -> None:
    rings: list[list[int]] = []
    for y in (y0, y1):
        ring = []
        for index in range(sides):
            angle = (math.tau * index) / sides
            ring.append(builder.add_vertex((math.cos(angle) * radius_x, y, math.sin(angle) * radius_z)))
        rings.append(ring)
    for index in range(sides):
        a = rings[0][index]
        b = rings[0][(index + 1) % sides]
        c = rings[1][(index + 1) % sides]
        d = rings[1][index]
        builder.add_quad(material, a, b, c, d)
    center_bottom = builder.add_vertex((0.0, y0, 0.0))
    center_top = builder.add_vertex((0.0, y1, 0.0))
    for index in range(sides):
        builder.add_face(material, center_bottom, rings[0][(index + 1) % sides], rings[0][index])
        builder.add_face(material, center_top, rings[1][index], rings[1][(index + 1) % sides])


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
        specular = "0.2200 0.2200 0.2200" if "crystal" in name or "gem" in name else "0.1000 0.1000 0.1000"
        lines.extend([f"newmtl {name}", f"Kd {r:.4f} {g:.4f} {b:.4f}", "Ka 0.7000 0.7000 0.7000", f"Ks {specular}", "Ns 48.0000", ""])
    output_mtl.write_text("\n".join(lines), encoding="utf-8")


def _write_obj(output_obj: Path, mtl_name: str, builder: _ObjBuilder) -> None:
    lines = ["# CubeLite procedural repair mesh", f"mtllib {mtl_name}"]
    for vertex in builder.vertices:
        lines.append(f"v {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}")
    normals = [_face_normal(builder.vertices[a - 1], builder.vertices[b - 1], builder.vertices[c - 1]) for _, (a, b, c) in builder.faces]
    for normal in normals:
        lines.append(f"vn {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}")
    current = ""
    for index, (material, (a, b, c)) in enumerate(builder.faces, start=1):
        if material != current:
            lines.append(f"usemtl {material}")
            current = material
        lines.append(f"f {a}//{index} {b}//{index} {c}//{index}")
    output_obj.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _face_normal(a: tuple[float, float, float], b: tuple[float, float, float], c: tuple[float, float, float]) -> tuple[float, float, float]:
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    length = max(math.sqrt(nx * nx + ny * ny + nz * nz), 1e-8)
    return nx / length, ny / length, nz / length
