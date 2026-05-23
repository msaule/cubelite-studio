from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from pathlib import Path


@dataclass
class SemanticMaterializeResult:
    success: bool
    output_obj_path: str | None
    output_mtl_path: str | None
    material_count: int = 0
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


MATERIAL_COLORS: dict[str, tuple[float, float, float]] = {
    "wood_main": (0.70, 0.41, 0.18),
    "wood_dark": (0.43, 0.24, 0.10),
    "wood_light": (0.88, 0.61, 0.30),
    "metal_dark": (0.32, 0.33, 0.36),
    "metal_light": (0.70, 0.72, 0.78),
    "metal_gold": (0.88, 0.63, 0.24),
    "crystal": (0.42, 0.90, 0.98),
    "crystal_dark": (0.34, 0.20, 0.78),
    "crystal_green": (0.24, 0.92, 0.48),
    "toy": (0.90, 0.42, 0.48),
    "sci_panel": (0.22, 0.28, 0.31),
    "sci_glow": (0.25, 0.90, 0.88),
    "clay": (0.52, 0.52, 0.45),
}


def materialize_obj_semantically(input_obj: Path, output_obj: Path, prompt: str) -> SemanticMaterializeResult:
    if not input_obj.exists():
        return SemanticMaterializeResult(False, None, None, error_message="Input OBJ does not exist.")
    try:
        vertices, faces = _parse_obj(input_obj)
        if not vertices or not faces:
            return SemanticMaterializeResult(False, None, None, error_message="Input OBJ has no usable vertices/faces.")
        output_obj.parent.mkdir(parents=True, exist_ok=True)
        output_mtl = output_obj.with_suffix(".mtl")
        bounds = _bounds(vertices)
        assignments: list[str] = []
        material_colors: dict[str, tuple[float, float, float]] = {}
        for face in faces:
            material_key = _assign_material(prompt, vertices, face)
            color = _procedural_face_color(material_key, prompt, vertices, face, bounds)
            material_name = _material_name(material_key, color)
            assignments.append(material_name)
            material_colors[material_name] = color
        _write_mtl(output_mtl, sorted(set(assignments)), material_colors)
        _write_obj(output_obj, output_mtl.name, vertices, faces, assignments)
        return SemanticMaterializeResult(True, str(output_obj), str(output_mtl), len(set(assignments)))
    except Exception as exc:
        return SemanticMaterializeResult(False, None, None, error_message=f"Semantic materialization failed: {exc}")


def _parse_obj(path: Path) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("v "):
            parts = line.split()
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif line.startswith("f "):
            indices: list[int] = []
            for token in line.split()[1:]:
                index = int(token.split("/")[0])
                if index < 0:
                    index = len(vertices) + index + 1
                indices.append(index - 1)
            for offset in range(1, len(indices) - 1):
                faces.append((indices[0], indices[offset], indices[offset + 1]))
    return vertices, faces


def _assign_material(prompt: str, vertices: list[tuple[float, float, float]], face: tuple[int, int, int]) -> str:
    lower = prompt.lower()
    centroid = tuple(sum(vertices[index][axis] for index in face) / 3 for axis in range(3))
    bounds = _bounds(vertices)
    normalized = _normalize_point(centroid, bounds)
    normal = _face_normal(vertices, face)
    if "sword" in lower:
        longest_axis = _longest_axis(bounds)
        t = normalized[longest_axis]
        if abs(t) > 0.42:
            return "crystal" if any(word in lower for word in ("crystal", "gem", "magic")) else "metal_light"
        if abs(t) < 0.10 and any(word in lower for word in ("green", "emerald", "gem")):
            return "crystal_green"
        if abs(t) < 0.18:
            return "metal_gold" if any(word in lower for word in ("fantasy", "gold", "medieval")) else "metal_dark"
        return "metal_dark"
    if any(word in lower for word in ("sci-fi", "scifi", "supply")):
        if int(abs(normalized[0] * 7) + abs(normalized[1] * 5) + abs(normalized[2] * 3)) % 7 == 0:
            return "sci_glow"
        return "sci_panel"
    if any(word in lower for word in ("toy", "cute")):
        return "toy"
    if any(word in lower for word in ("wood", "crate", "chest", "boat", "barrel")):
        metal_requested = any(word in lower for word in ("metal", "band", "hinge", "lock", "rivet", "trim"))
        if metal_requested and _looks_like_metal_band(normalized, normal, lower):
            return "metal_gold" if "fantasy" in lower else "metal_dark"
        if "crate" in lower and _looks_like_cross_plank(normalized, normal):
            return "wood_dark"
        return "wood_main"
    if any(word in lower for word in ("crystal", "gem", "magic")):
        return "crystal"
    return "clay"


def _looks_like_metal_band(normalized: tuple[float, float, float], normal: tuple[float, float, float], prompt: str) -> bool:
    x, y, z = normalized
    side_facing = abs(normal[0]) > 0.55 or abs(normal[2]) > 0.55
    top_or_front = abs(normal[1]) > 0.55 or side_facing
    vertical_strap = abs(x) < 0.055 or abs(z) < 0.055
    rim_trim = (abs(y) > 0.84) and (abs(x) > 0.78 or abs(z) > 0.78)
    lid_band = ("chest" in prompt) and (0.22 < y < 0.30) and (abs(x) > 0.62 or abs(z) > 0.62)
    return top_or_front and (vertical_strap or rim_trim or lid_band)


def _looks_like_cross_plank(normalized: tuple[float, float, float], normal: tuple[float, float, float]) -> bool:
    x, y, z = normalized
    side_facing = abs(normal[0]) > 0.45 or abs(normal[2]) > 0.45
    diagonal_hint = abs(abs(x) - abs(y)) < 0.08 or abs(abs(z) - abs(y)) < 0.08
    edge_frame = abs(x) > 0.80 or abs(y) > 0.80 or abs(z) > 0.80
    return side_facing and (diagonal_hint or edge_frame)


def _face_normal(vertices: list[tuple[float, float, float]], face: tuple[int, int, int]) -> tuple[float, float, float]:
    ax, ay, az = vertices[face[0]]
    bx, by, bz = vertices[face[1]]
    cx, cy, cz = vertices[face[2]]
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    length = max((nx * nx + ny * ny + nz * nz) ** 0.5, 1e-8)
    return nx / length, ny / length, nz / length


def _procedural_face_color(
    material_key: str,
    prompt: str,
    vertices: list[tuple[float, float, float]],
    face: tuple[int, int, int],
    bounds: tuple[tuple[float, float, float], tuple[float, float, float]],
) -> tuple[float, float, float]:
    centroid = tuple(sum(vertices[index][axis] for index in face) / 3 for axis in range(3))
    normalized = _normalize_point(centroid, bounds)
    noise = _stable_noise(centroid)
    if material_key.startswith("wood"):
        grain = 0.5 + 0.5 * math.sin((centroid[0] * 18.0) + (centroid[2] * 9.0) + (centroid[1] * 3.0))
        grain = max(0.0, min(1.0, grain * 0.72 + noise * 0.28))
        if material_key == "wood_dark":
            return _mix_float(MATERIAL_COLORS["wood_dark"], MATERIAL_COLORS["wood_main"], 0.20 + grain * 0.18)
        return _mix_float(MATERIAL_COLORS["wood_dark"], MATERIAL_COLORS["wood_light"], 0.34 + grain * 0.36)
    if material_key.startswith("metal"):
        base = MATERIAL_COLORS.get(material_key, MATERIAL_COLORS["metal_light"])
        highlight = 0.10 + 0.12 * max(normalized)
        return _mix_float(base, (1.0, 0.88, 0.52) if material_key == "metal_gold" else (0.86, 0.88, 0.94), highlight)
    if material_key.startswith("crystal"):
        base = MATERIAL_COLORS.get(material_key, MATERIAL_COLORS["crystal"])
        glint = 0.12 + 0.22 * max(0.0, math.sin((centroid[0] - centroid[1]) * 12.0))
        return _mix_float(base, (0.88, 1.0, 1.0), glint)
    if material_key == "sci_glow":
        return MATERIAL_COLORS["sci_glow"]
    if material_key == "sci_panel":
        panel = 0.18 + 0.14 * noise
        return _mix_float(MATERIAL_COLORS["sci_panel"], (0.46, 0.54, 0.58), panel)
    return MATERIAL_COLORS.get(material_key, MATERIAL_COLORS["clay"])


def _material_name(material_key: str, color: tuple[float, float, float]) -> str:
    channels = tuple(max(0, min(31, int(round(value * 31)))) for value in color)
    return f"{material_key}_{channels[0]:02d}_{channels[1]:02d}_{channels[2]:02d}"


def _stable_noise(point: tuple[float, float, float]) -> float:
    value = 0
    for coord in point:
        value ^= int((coord + 13.37) * 10000) & 0xFFFFFFFF
        value = (value * 1664525 + 1013904223) & 0xFFFFFFFF
    return (value % 1000) / 1000.0


def _mix_float(a: tuple[float, float, float], b: tuple[float, float, float], amount: float) -> tuple[float, float, float]:
    amount = max(0.0, min(1.0, amount))
    return tuple(max(0.0, min(1.0, a[i] * (1 - amount) + b[i] * amount)) for i in range(3))


def _bounds(vertices: list[tuple[float, float, float]]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    mins = tuple(min(vertex[axis] for vertex in vertices) for axis in range(3))
    maxs = tuple(max(vertex[axis] for vertex in vertices) for axis in range(3))
    return mins, maxs


def _normalize_point(point, bounds) -> tuple[float, float, float]:
    mins, maxs = bounds
    values = []
    for axis in range(3):
        span = max(maxs[axis] - mins[axis], 1e-6)
        values.append(((point[axis] - mins[axis]) / span) * 2 - 1)
    return tuple(values)


def _longest_axis(bounds) -> int:
    mins, maxs = bounds
    spans = [maxs[axis] - mins[axis] for axis in range(3)]
    return max(range(3), key=lambda axis: spans[axis])


def _write_mtl(output_mtl: Path, materials: list[str], material_colors: dict[str, tuple[float, float, float]] | None = None) -> None:
    lines = ["# CubeLite semantic material set"]
    for material in materials:
        r, g, b = (material_colors or {}).get(material, MATERIAL_COLORS.get(material, MATERIAL_COLORS["clay"]))
        lines.extend(
            [
                f"newmtl {material}",
                f"Kd {r:.4f} {g:.4f} {b:.4f}",
                "Ka 0.8500 0.8500 0.8500",
                "Ks 0.0500 0.0500 0.0500",
                "Ns 24.0000",
                "",
            ]
        )
    output_mtl.write_text("\n".join(lines), encoding="utf-8")


def _write_obj(output_obj: Path, mtl_name: str, vertices, faces, assignments) -> None:
    with output_obj.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# CubeLite semantic material OBJ\n")
        handle.write(f"mtllib {mtl_name}\n")
        for vertex in vertices:
            handle.write(f"v {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}\n")
        current = None
        for face, material in zip(faces, assignments):
            if material != current:
                handle.write(f"usemtl {material}\n")
                current = material
            a, b, c = (face[0] + 1, face[1] + 1, face[2] + 1)
            handle.write(f"f {a} {b} {c}\n")
