from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from textwrap import wrap


@dataclass
class TexturedRenderResult:
    success: bool
    output_path: str | None
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def render_textured_inspection_plate(
    textured_obj: Path,
    albedo_path: Path,
    output_png: Path,
    title: str = "CubeLite Textured Mesh",
    show_edges: bool = False,
) -> TexturedRenderResult:
    if not textured_obj.exists():
        return TexturedRenderResult(False, None, "Textured OBJ does not exist.")
    if not albedo_path.exists():
        return TexturedRenderResult(False, None, "Albedo texture does not exist.")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        from PIL import Image
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    except Exception as exc:
        return TexturedRenderResult(False, None, f"Textured rendering dependencies are unavailable: {exc}")

    try:
        vertices, faces, uvs, uv_faces = _parse_textured_obj(textured_obj, np)
        if len(vertices) == 0 or len(faces) == 0:
            return TexturedRenderResult(False, None, "Textured OBJ has no renderable faces.")
        texture = Image.open(albedo_path).convert("RGB")
        triangles = vertices[faces]
        colors = [_face_color(uvs[uv_face], texture, triangles[index]) for index, uv_face in enumerate(uv_faces)]
        mins = vertices.min(axis=0)
        maxs = vertices.max(axis=0)
        spans = maxs - mins
        max_span = max(float(spans.max()), 0.5)
        margin = max_span * 0.08
        aspect = tuple(max(float(span), max_span * 0.08) for span in spans)
        views = _inspection_views(spans)
        output_png.parent.mkdir(parents=True, exist_ok=True)
        fig = plt.figure(figsize=(12, 8), dpi=150)
        fig.patch.set_facecolor("#f7f8fa")
        fig.suptitle("\n".join(wrap(title, width=84, max_lines=2, placeholder="...")), fontsize=13, fontweight="bold", y=0.98)

        edge_color = (0.05, 0.05, 0.05, 0.16) if show_edges else "none"
        line_width = 0.08 if show_edges else 0.0
        for index, (label, elev, azim) in enumerate(views, start=1):
            ax = fig.add_subplot(2, 3, index, projection="3d")
            collection = Poly3DCollection(
                triangles,
                facecolors=colors,
                edgecolor=edge_color,
                linewidth=line_width,
                antialiaseds=True,
            )
            ax.add_collection3d(collection)
            ax.set_xlim(mins[0] - margin, maxs[0] + margin)
            ax.set_ylim(mins[1] - margin, maxs[1] + margin)
            ax.set_zlim(mins[2] - margin, maxs[2] + margin)
            ax.view_init(elev=elev, azim=azim)
            ax.set_box_aspect(aspect)
            ax.set_axis_off()
            ax.set_title(label, fontsize=9, pad=2)
            ax.set_facecolor("#f7f8fa")

        plt.tight_layout(rect=(0, 0, 1, 0.95), pad=0.4)
        fig.savefig(output_png, bbox_inches="tight", pad_inches=0.12)
        plt.close(fig)
        return TexturedRenderResult(True, str(output_png))
    except Exception as exc:
        try:
            plt.close("all")
        except Exception:
            pass
        return TexturedRenderResult(False, None, f"Textured render failed: {exc}")


def render_material_inspection_plate(
    material_obj: Path,
    output_png: Path,
    title: str = "CubeLite Material Mesh",
    show_edges: bool = False,
) -> TexturedRenderResult:
    if not material_obj.exists():
        return TexturedRenderResult(False, None, "Material OBJ does not exist.")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    except Exception as exc:
        return TexturedRenderResult(False, None, f"Material rendering dependencies are unavailable: {exc}")

    try:
        vertices, faces, material_names = _parse_material_obj(material_obj, np)
        if len(vertices) == 0 or len(faces) == 0:
            return TexturedRenderResult(False, None, "Material OBJ has no renderable faces.")
        material_colors = _parse_mtl_colors(material_obj)
        triangles = vertices[faces]
        colors = [_shade_color(material_colors.get(material, (0.55, 0.55, 0.50)), triangles[index]) for index, material in enumerate(material_names)]
        return _render_plate(vertices, triangles, colors, output_png, title, show_edges, plt, Poly3DCollection)
    except Exception as exc:
        try:
            plt.close("all")
        except Exception:
            pass
        return TexturedRenderResult(False, None, f"Material render failed: {exc}")


def render_material_showcase_plate(
    material_obj: Path,
    output_png: Path,
    title: str = "CubeLite Material Mesh",
    show_edges: bool = True,
) -> TexturedRenderResult:
    if not material_obj.exists():
        return TexturedRenderResult(False, None, "Material OBJ does not exist.")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    except Exception as exc:
        return TexturedRenderResult(False, None, f"Material rendering dependencies are unavailable: {exc}")

    try:
        vertices, faces, material_names = _parse_material_obj(material_obj, np)
        if len(vertices) == 0 or len(faces) == 0:
            return TexturedRenderResult(False, None, "Material OBJ has no renderable faces.")
        material_colors = _parse_mtl_colors(material_obj)
        triangles = vertices[faces]
        colors = [_shade_color(material_colors.get(material, (0.55, 0.55, 0.50)), triangles[index]) for index, material in enumerate(material_names)]
        return _render_showcase_plate(vertices, triangles, colors, output_png, title, show_edges, plt, Poly3DCollection)
    except Exception as exc:
        try:
            plt.close("all")
        except Exception:
            pass
        return TexturedRenderResult(False, None, f"Material showcase render failed: {exc}")


def _render_showcase_plate(vertices, triangles, colors, output_png: Path, title: str, show_edges: bool, plt, Poly3DCollection) -> TexturedRenderResult:
    mins = vertices.min(axis=0)
    maxs = vertices.max(axis=0)
    spans = maxs - mins
    max_span = max(float(spans.max()), 0.5)
    margin = max_span * 0.075
    aspect = tuple(max(float(span), max_span * 0.08) for span in spans)
    output_png.parent.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(13, 8), dpi=160)
    fig.patch.set_facecolor("#f6f7f9")
    fig.suptitle("\n".join(wrap(title, width=76, max_lines=2, placeholder="...")), fontsize=14, fontweight="bold", y=0.97)
    grid = fig.add_gridspec(2, 3, width_ratios=[1.15, 1.15, 0.92], height_ratios=[1, 1], wspace=0.02, hspace=0.12)
    views = [
        ("Hero face", 90, -90, grid[:, :2]),
        ("3/4 shape", 34, -48, grid[0, 2]),
        ("Edge depth", 4, 0, grid[1, 2]),
    ]
    edge_color = (0.03, 0.03, 0.035, 0.20) if show_edges else "none"
    line_width = 0.10 if show_edges else 0.0
    for label, elev, azim, slot in views:
        ax = fig.add_subplot(slot, projection="3d")
        collection = Poly3DCollection(
            triangles,
            facecolors=colors,
            edgecolor=edge_color,
            linewidth=line_width,
            antialiaseds=True,
        )
        ax.add_collection3d(collection)
        ax.set_xlim(mins[0] - margin, maxs[0] + margin)
        ax.set_ylim(mins[1] - margin, maxs[1] + margin)
        ax.set_zlim(mins[2] - margin, maxs[2] + margin)
        ax.view_init(elev=elev, azim=azim)
        ax.set_box_aspect(aspect)
        ax.set_axis_off()
        ax.set_title(label, fontsize=9, pad=0)
        ax.set_facecolor("#f6f7f9")

    fig.savefig(output_png, bbox_inches="tight", pad_inches=0.14)
    plt.close(fig)
    return TexturedRenderResult(True, str(output_png))


def _render_plate(vertices, triangles, colors, output_png: Path, title: str, show_edges: bool, plt, Poly3DCollection) -> TexturedRenderResult:
    mins = vertices.min(axis=0)
    maxs = vertices.max(axis=0)
    spans = maxs - mins
    max_span = max(float(spans.max()), 0.5)
    margin = max_span * 0.08
    aspect = tuple(max(float(span), max_span * 0.08) for span in spans)

    views = _inspection_views(spans)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(12, 8), dpi=150)
    fig.patch.set_facecolor("#f7f8fa")
    fig.suptitle("\n".join(wrap(title, width=84, max_lines=2, placeholder="...")), fontsize=13, fontweight="bold", y=0.98)

    edge_color = (0.05, 0.05, 0.05, 0.18) if show_edges else "none"
    line_width = 0.08 if show_edges else 0.0
    for index, (label, elev, azim) in enumerate(views, start=1):
        ax = fig.add_subplot(2, 3, index, projection="3d")
        collection = Poly3DCollection(
            triangles,
            facecolors=colors,
            edgecolor=edge_color,
            linewidth=line_width,
            antialiaseds=True,
        )
        ax.add_collection3d(collection)
        ax.set_xlim(mins[0] - margin, maxs[0] + margin)
        ax.set_ylim(mins[1] - margin, maxs[1] + margin)
        ax.set_zlim(mins[2] - margin, maxs[2] + margin)
        ax.view_init(elev=elev, azim=azim)
        ax.set_box_aspect(aspect)
        ax.set_axis_off()
        ax.set_title(label, fontsize=9, pad=2)
        ax.set_facecolor("#f7f8fa")

    plt.tight_layout(rect=(0, 0, 1, 0.95), pad=0.4)
    fig.savefig(output_png, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return TexturedRenderResult(True, str(output_png))


def _inspection_views(spans) -> list[tuple[str, float, float]]:
    x_span, y_span, z_span = (float(value) for value in spans)
    if y_span > max(x_span, z_span) * 1.6 and z_span < max(x_span, y_span) * 0.18:
        return [
            ("Face", 90, -90),
            ("3/4 Face", 38, -52),
            ("Edge", 0, 0),
            ("Back Face", -90, -90),
            ("Hilt", 0, -90),
            ("Guard Angle", 26, 136),
        ]
    return [
        ("Front", 0, -90),
        ("Right", 0, 0),
        ("Back", 0, 90),
        ("Left", 0, 180),
        ("Top", 90, -90),
        ("3/4", 28, 38),
    ]


def _parse_textured_obj(path: Path, np):
    vertices: list[tuple[float, float, float]] = []
    uvs: list[tuple[float, float]] = []
    faces: list[tuple[int, int, int]] = []
    uv_faces: list[tuple[int, int, int]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("v "):
            parts = line.split()
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif line.startswith("vt "):
            parts = line.split()
            uvs.append((float(parts[1]), float(parts[2])))
        elif line.startswith("f "):
            vertex_indices: list[int] = []
            uv_indices: list[int] = []
            for token in line.split()[1:]:
                parts = token.split("/")
                if not parts[0]:
                    continue
                vertex_index = int(parts[0]) - 1
                uv_index = int(parts[1]) - 1 if len(parts) > 1 and parts[1] else vertex_index
                vertex_indices.append(vertex_index)
                uv_indices.append(uv_index)
            for offset in range(1, len(vertex_indices) - 1):
                faces.append((vertex_indices[0], vertex_indices[offset], vertex_indices[offset + 1]))
                uv_faces.append((uv_indices[0], uv_indices[offset], uv_indices[offset + 1]))
    return np.asarray(vertices), np.asarray(faces, dtype=int), np.asarray(uvs), np.asarray(uv_faces, dtype=int)


def _parse_material_obj(path: Path, np):
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    material_names: list[str] = []
    current_material = "default"
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("v "):
            parts = line.split()
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif line.startswith("usemtl "):
            current_material = line.split(maxsplit=1)[1].strip() or "default"
        elif line.startswith("f "):
            vertex_indices: list[int] = []
            for token in line.split()[1:]:
                parts = token.split("/")
                if not parts[0]:
                    continue
                vertex_index = int(parts[0])
                if vertex_index < 0:
                    vertex_index = len(vertices) + vertex_index + 1
                vertex_indices.append(vertex_index - 1)
            for offset in range(1, len(vertex_indices) - 1):
                faces.append((vertex_indices[0], vertex_indices[offset], vertex_indices[offset + 1]))
                material_names.append(current_material)
    return np.asarray(vertices), np.asarray(faces, dtype=int), material_names


def _parse_mtl_colors(obj_path: Path) -> dict[str, tuple[float, float, float]]:
    colors: dict[str, tuple[float, float, float]] = {"default": (0.55, 0.55, 0.50)}
    mtl_paths: list[Path] = []
    for line in obj_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("mtllib "):
            mtl_paths.append(obj_path.parent / line.split(maxsplit=1)[1].strip())
    for mtl_path in mtl_paths:
        if not mtl_path.exists():
            continue
        current = ""
        for line in mtl_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("newmtl "):
                current = line.split(maxsplit=1)[1].strip()
            elif current and line.startswith("Kd "):
                parts = line.split()
                colors[current] = (float(parts[1]), float(parts[2]), float(parts[3]))
    return colors


def _face_color(uv_triangle, texture, triangle):
    import numpy as np

    width, height = texture.size
    pixels = texture.load()
    samples = []
    centroid = uv_triangle.mean(axis=0)
    sample_points = [centroid, *uv_triangle]
    for u, v in sample_points:
        x = max(0, min(width - 1, int(float(u) * (width - 1))))
        y = max(0, min(height - 1, int((1.0 - float(v)) * (height - 1))))
        samples.append(pixels[x, y][:3])
    rgb = np.asarray(samples, dtype=float).mean(axis=0) / 255.0
    return _shade_color(tuple(float(value) for value in rgb), triangle)


def _shade_color(rgb: tuple[float, float, float], triangle):
    import numpy as np

    rgb_array = np.asarray(rgb, dtype=float)
    normal = np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
    length = max(float(np.linalg.norm(normal)), 1e-6)
    normal = normal / length
    light = np.asarray([0.35, -0.55, 0.76])
    light = light / max(float(np.linalg.norm(light)), 1e-6)
    shade = 0.76 + 0.30 * max(0.0, float(np.dot(normal, light)))
    shaded = np.clip(rgb_array * shade, 0, 1)
    return (float(shaded[0]), float(shaded[1]), float(shaded[2]), 0.98)
