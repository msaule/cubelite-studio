from pathlib import Path

from PIL import Image, ImageDraw

from app.quality.render_quality import assess_render_quality


def test_render_quality_scores_nonblank_plate(tmp_path: Path) -> None:
    path = tmp_path / "plate.png"
    image = Image.new("RGB", (256, 256), "#f7f8fa")
    draw = ImageDraw.Draw(image)
    draw.rectangle((64, 48, 192, 208), fill="#6688aa", outline="#111111", width=4)
    image.save(path)

    report = assess_render_quality(path)

    assert report.score > 50
    assert report.metrics["edge_strength"] is not None


def test_render_quality_warns_on_missing_plate() -> None:
    report = assess_render_quality(None)

    assert report.score == 50
    assert report.warnings
