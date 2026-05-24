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
    "gem_light": (0.58, 1.00, 0.72),
    "gem_dark": (0.04, 0.38, 0.20),
    "rune_purple": (0.58, 0.30, 1.00),
    "rune_pink": (1.00, 0.36, 0.78),
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
    _add_blade_facets(builder)
    _add_blade_socket(builder)
    _add_grip(builder)
    _add_guard(builder)
    _add_pommel(builder)
    _add_diamond(builder, "gold_light", center=(0.0, -0.020, 0.088), radius=0.095, depth=0.012)
    _add_diamond(builder, "gem_light", center=(0.0, -0.020, 0.104), radius=0.062, depth=0.025)
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
    # Long fantasy-sword silhouette. Keep the blade readable at Roblox scale
    # without letting the proportions collapse into a dagger.
    outline = [
        (-0.205, 0.030),
        (-0.340, 0.165),
        (-0.285, 0.390),
        (-0.250, 0.820),
        (-0.215, 1.330),
        (-0.162, 1.860),
        (-0.095, 2.330),
        (0.000, 2.620),
        (0.095, 2.330),
        (0.162, 1.860),
        (0.215, 1.330),
        (0.250, 0.820),
        (0.285, 0.390),
        (0.340, 0.165),
        (0.205, 0.030),
    ]
    _add_extruded_polygon(builder, "crystal_core", outline, half_depth=0.075)
    inner_left = [
        (-0.040, 0.145),
        (-0.180, 0.360),
        (-0.165, 1.080),
        (-0.115, 1.720),
        (-0.048, 2.245),
        (0.000, 2.470),
        (0.000, 0.095),
    ]
    inner_right = [(-x, y) for x, y in reversed(inner_left)]
    _add_surface_polygon(builder, "crystal_highlight", inner_left, z=0.084)
    _add_surface_polygon(builder, "crystal_edge", inner_right, z=0.085)
    _add_surface_polygon(builder, "crystal_shadow", inner_left, z=-0.084, reverse=True)
    _add_surface_polygon(builder, "crystal_deep", inner_right, z=-0.085, reverse=True)
    _add_raised_ridge(builder, y0=0.135, y1=2.380, z=0.096)


def _add_blade_facets(builder: _ObjBuilder) -> None:
    _add_surface_polygon(
        builder,
        "crystal_shadow",
        [(-0.255, 0.190), (-0.200, 0.420), (-0.170, 1.170), (-0.110, 1.860), (-0.048, 2.240), (-0.126, 1.840), (-0.205, 0.405)],
        z=0.092,
    )
    _add_surface_polygon(
        builder,
        "crystal_highlight",
        [(0.255, 0.190), (0.200, 0.420), (0.170, 1.170), (0.110, 1.860), (0.048, 2.240), (0.126, 1.840), (0.205, 0.405)],
        z=0.093,
        reverse=True,
    )
    _add_oriented_box_xy(builder, "crystal_deep", (-0.055, 0.215), (-0.018, 1.950), half_width=0.010, half_depth=0.098)
    _add_oriented_box_xy(builder, "crystal_deep", (0.055, 0.215), (0.018, 1.950), half_width=0.010, half_depth=0.098)
    _add_oriented_box_xy(builder, "crystal_highlight", (0.000, 0.200), (0.000, 2.340), half_width=0.009, half_depth=0.108)
    for y, radius, material in (
        (0.470, 0.030, "rune_purple"),
        (0.820, 0.026, "rune_pink"),
        (1.180, 0.030, "rune_purple"),
        (1.540, 0.026, "rune_pink"),
        (1.900, 0.024, "rune_purple"),
    ):
        _add_diamond(builder, material, center=(0.0, y, 0.106), radius=radius, depth=0.010)
    for y, material in ((0.650, "rune_pink"), (1.360, "rune_purple"), (2.045, "rune_pink")):
        _add_oriented_box_xy(builder, material, (-0.082, y), (0.082, y + 0.018), half_width=0.006, half_depth=0.111)


def _add_blade_socket(builder: _ObjBuilder) -> None:
    _add_box(builder, "metal_edge", (-0.185, -0.020, -0.098), (0.185, 0.105, 0.098))
    _add_box(builder, "gold_shadow", (-0.155, -0.070, -0.098), (0.155, 0.010, 0.098))
    _add_diamond(builder, "gold_light", center=(0.0, 0.045, 0.105), radius=0.070, depth=0.014)
    _add_diamond(builder, "gem_green", center=(0.0, 0.045, 0.124), radius=0.046, depth=0.020)


def _add_grip(builder: _ObjBuilder) -> None:
    _add_octagonal_prism(builder, "leather", y0=-0.94, y1=0.030, radius_x=0.076, radius_z=0.058, sides=12)
    for index, y in enumerate((-0.835, -0.700, -0.565, -0.430, -0.295, -0.160, -0.055)):
        slant = 0.055 if index % 2 == 0 else -0.055
        _add_oriented_box_xy(builder, "gold_shadow", (-0.105, y - 0.032), (0.105, y + slant), half_width=0.020, half_depth=0.070)
    _add_octagonal_prism(builder, "grip_wrap", y0=-0.980, y1=-0.930, radius_x=0.102, radius_z=0.074, sides=12)
    _add_octagonal_prism(builder, "grip_wrap", y0=0.000, y1=0.055, radius_x=0.108, radius_z=0.074, sides=12)


def _add_guard(builder: _ObjBuilder) -> None:
    _add_box(builder, "metal_mid", (-0.220, -0.075, -0.106), (0.220, 0.065, 0.106))
    left_wing = [(-0.760, -0.120), (-0.620, 0.010), (-0.330, 0.060), (-0.145, 0.025), (-0.230, -0.115), (-0.550, -0.225)]
    right_wing = [(-x, y) for x, y in reversed(left_wing)]
    _add_extruded_polygon(builder, "gold", left_wing, half_depth=0.080)
    _add_extruded_polygon(builder, "gold", right_wing, half_depth=0.080)
    _add_surface_polygon(builder, "gold_light", [(-0.650, -0.095), (-0.545, -0.030), (-0.315, 0.025), (-0.240, -0.018), (-0.505, -0.155)], z=0.088)
    _add_surface_polygon(builder, "gold_light", [(0.650, -0.095), (0.545, -0.030), (0.315, 0.025), (0.240, -0.018), (0.505, -0.155)], z=0.088, reverse=True)
    _add_oriented_box_xy(builder, "gold_shadow", (-0.650, -0.130), (-0.275, -0.018), half_width=0.012, half_depth=0.096)
    _add_oriented_box_xy(builder, "gold_shadow", (0.275, -0.018), (0.650, -0.130), half_width=0.012, half_depth=0.096)
    _add_oriented_box_xy(builder, "gold_light", (-0.560, -0.060), (-0.260, 0.018), half_width=0.008, half_depth=0.102)
    _add_oriented_box_xy(builder, "gold_light", (0.260, 0.018), (0.560, -0.060), half_width=0.008, half_depth=0.102)
    _add_diamond(builder, "gold_shadow", center=(-0.765, -0.125, 0.0), radius=0.070, depth=0.060)
    _add_diamond(builder, "gold_shadow", center=(0.765, -0.125, 0.0), radius=0.070, depth=0.060)
    _add_diamond(builder, "gem_green", center=(-0.390, -0.045, 0.095), radius=0.038, depth=0.016)
    _add_diamond(builder, "gem_green", center=(0.390, -0.045, 0.095), radius=0.038, depth=0.016)


def _add_pommel(builder: _ObjBuilder) -> None:
    _add_octagonal_prism(builder, "gold", y0=-1.110, y1=-0.940, radius_x=0.122, radius_z=0.082, sides=8)
    _add_octagonal_prism(builder, "gold_light", y0=-1.050, y1=-0.995, radius_x=0.150, radius_z=0.094, sides=8)
    _add_diamond(builder, "gem_green", center=(0.0, -1.020, 0.102), radius=0.044, depth=0.018)
    _add_diamond(builder, "gold_shadow", center=(0.0, -1.255, 0.0), radius=0.120, depth=0.078)


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
        if material == "crystal_core":
            edge_material = "crystal_edge" if index in {0, 1, 10, 11, 12, 13, 14} else ("crystal_shadow" if index in {5, 6, 7, 8, 9} else material)
            front_material = "crystal_highlight" if index < count // 2 else material
            back_material = "crystal_deep" if index < count // 2 else "crystal_shadow"
        elif material == "gold":
            edge_material = "gold_shadow"
            front_material = "gold_light" if index < count // 2 else "gold"
            back_material = "gold_shadow"
        else:
            edge_material = material
            front_material = material
            back_material = material
        builder.add_face(front_material, front_center, front[index], front[next_index])
        builder.add_face(back_material, back_center, back[next_index], back[index])
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
