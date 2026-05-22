from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from textwrap import wrap


@dataclass
class RenderResult:
    success: bool
    output_path: str | None
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def render_mesh_preview(input_obj: Path, output_png: Path, title: str = "CubeLite Preview") -> RenderResult:
    """Render a simple local PNG preview for OBJ meshes.

    This is intentionally lightweight: it creates an isometric-style preview for
    benchmark reports and export packages without requiring Blender or Roblox
    Studio to be installed.
    """
    if not input_obj.exists():
        return RenderResult(False, None, "Input OBJ does not exist.")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    except Exception as exc:
        return RenderResult(
            False,
            None,
            f"Preview rendering dependencies are unavailable: {exc}. Install matplotlib to enable previews.",
        )

    try:
        vertices, faces = _load_vertices_and_faces(input_obj, np)
        if len(vertices) == 0 or len(faces) == 0:
            return RenderResult(False, None, "Mesh has no vertices or faces to render.")

        output_png.parent.mkdir(parents=True, exist_ok=True)
        fig = plt.figure(figsize=(6, 6), dpi=160)
        ax = fig.add_subplot(111, projection="3d")
        triangles = vertices[faces]
        collection = Poly3DCollection(
            triangles,
            facecolor=(0.42, 0.62, 0.82, 0.92),
            edgecolor=(0.08, 0.12, 0.18, 0.35),
            linewidth=0.35,
        )
        ax.add_collection3d(collection)

        mins = vertices.min(axis=0)
        maxs = vertices.max(axis=0)
        center = (mins + maxs) / 2
        radius = max(float((maxs - mins).max()) / 2, 0.5)
        ax.set_xlim(center[0] - radius, center[0] + radius)
        ax.set_ylim(center[1] - radius, center[1] + radius)
        ax.set_zlim(center[2] - radius, center[2] + radius)
        ax.view_init(elev=28, azim=38)
        ax.set_box_aspect((1, 1, 1))
        ax.set_axis_off()
        wrapped_title = "\n".join(wrap(title, width=48, max_lines=2, placeholder="..."))
        ax.set_title(wrapped_title, fontsize=9, pad=8)
        fig.patch.set_facecolor("#f7f8fa")
        ax.set_facecolor("#f7f8fa")
        plt.tight_layout(pad=0.2)
        fig.savefig(output_png, bbox_inches="tight", pad_inches=0.05)
        plt.close(fig)
        return RenderResult(True, str(output_png))
    except Exception as exc:
        try:
            plt.close("all")
        except Exception:
            pass
        return RenderResult(False, None, f"Preview rendering failed: {exc}")


def render_mesh_inspection_plate(input_obj: Path, output_png: Path, title: str = "CubeLite Mesh Inspection") -> RenderResult:
    """Render a multi-angle inspection plate for a generated OBJ.

    A single attractive angle can hide weak geometry. The inspection plate is
    meant for case studies and curation: it shows whether the asset reads from
    front, side, back, top, and a basic 3/4 view.
    """
    if not input_obj.exists():
        return RenderResult(False, None, "Input OBJ does not exist.")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    except Exception as exc:
        return RenderResult(
            False,
            None,
            f"Inspection rendering dependencies are unavailable: {exc}. Install matplotlib to enable render plates.",
        )

    try:
        vertices, faces = _load_vertices_and_faces(input_obj, np)
        if len(vertices) == 0 or len(faces) == 0:
            return RenderResult(False, None, "Mesh has no vertices or faces to render.")

        output_png.parent.mkdir(parents=True, exist_ok=True)
        triangles = vertices[faces]
        mins = vertices.min(axis=0)
        maxs = vertices.max(axis=0)
        center = (mins + maxs) / 2
        radius = max(float((maxs - mins).max()) / 2, 0.5)

        views = [
            ("Front", 0, -90),
            ("Right", 0, 0),
            ("Back", 0, 90),
            ("Left", 0, 180),
            ("Top", 90, -90),
            ("3/4", 28, 38),
        ]
        fig = plt.figure(figsize=(12, 8), dpi=150)
        fig.patch.set_facecolor("#f7f8fa")
        wrapped_title = "\n".join(wrap(title, width=84, max_lines=2, placeholder="..."))
        fig.suptitle(wrapped_title, fontsize=13, fontweight="bold", y=0.98)

        for index, (label, elev, azim) in enumerate(views, start=1):
            ax = fig.add_subplot(2, 3, index, projection="3d")
            collection = Poly3DCollection(
                triangles,
                facecolor=(0.42, 0.62, 0.82, 0.94),
                edgecolor=(0.08, 0.12, 0.18, 0.28),
                linewidth=0.25,
            )
            ax.add_collection3d(collection)
            ax.set_xlim(center[0] - radius, center[0] + radius)
            ax.set_ylim(center[1] - radius, center[1] + radius)
            ax.set_zlim(center[2] - radius, center[2] + radius)
            ax.view_init(elev=elev, azim=azim)
            ax.set_box_aspect((1, 1, 1))
            ax.set_axis_off()
            ax.set_title(label, fontsize=9, pad=2)
            ax.set_facecolor("#f7f8fa")

        plt.tight_layout(rect=(0, 0, 1, 0.95), pad=0.4)
        fig.savefig(output_png, bbox_inches="tight", pad_inches=0.12)
        plt.close(fig)
        return RenderResult(True, str(output_png))
    except Exception as exc:
        try:
            plt.close("all")
        except Exception:
            pass
        return RenderResult(False, None, f"Inspection rendering failed: {exc}")


def _load_vertices_and_faces(input_obj: Path, np):
    try:
        import trimesh

        loaded = trimesh.load(str(input_obj), force="scene")
        geometries = list(getattr(loaded, "geometry", {}).values()) if hasattr(loaded, "geometry") else [loaded]
        meshes = [mesh for mesh in geometries if hasattr(mesh, "vertices") and hasattr(mesh, "faces") and len(mesh.faces) > 0]
        if meshes:
            mesh = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]
            return np.asarray(mesh.vertices), np.asarray(mesh.faces)
    except Exception:
        pass

    vertices: list[tuple[float, float, float]] = []
    triangles: list[tuple[int, int, int]] = []
    for line in input_obj.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("v "):
            parts = line.split()
            if len(parts) >= 4:
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif line.startswith("f "):
            indices: list[int] = []
            for token in line.split()[1:]:
                index_text = token.split("/")[0]
                if not index_text:
                    continue
                index = int(index_text)
                if index < 0:
                    index = len(vertices) + index + 1
                indices.append(index - 1)
            for offset in range(1, max(1, len(indices) - 1)):
                if len(indices) >= offset + 2:
                    triangles.append((indices[0], indices[offset], indices[offset + 1]))
    return np.asarray(vertices), np.asarray(triangles, dtype=int)
