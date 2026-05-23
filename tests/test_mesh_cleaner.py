from pathlib import Path

from app.optimization.mesh_analyzer import analyze_mesh
from app.optimization.mesh_cleaner import remove_small_components


def test_mesh_cleaner_removes_tiny_disconnected_island(tmp_path: Path) -> None:
    obj = tmp_path / "two_components.obj"
    obj.write_text(
        "\n".join(
            [
                "v 0 0 0",
                "v 1 0 0",
                "v 0 1 0",
                "v 0 0 1",
                "v 5 5 5",
                "v 5.1 5 5",
                "v 5 5.1 5",
                "f 1 2 3",
                "f 1 2 4",
                "f 1 3 4",
                "f 2 3 4",
                "f 5 6 7",
            ]
        ),
        encoding="utf-8",
    )

    result = remove_small_components(obj, tmp_path / "cleaned.obj", min_face_ratio=0.5, min_faces=2)

    assert result.success
    assert result.removed_components == 1
    assert result.output_path
    stats = analyze_mesh(Path(result.output_path))
    assert stats.success
    assert stats.triangle_count == 4
