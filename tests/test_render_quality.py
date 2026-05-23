from pathlib import Path

from PIL import Image, ImageDraw

from app.quality.render_quality import assess_render_quality


def test_render_quality_allows_sparse_sword_plate(tmp_path: Path) -> None:
    image_path = tmp_path / "sword_plate.png"
    image = Image.new("RGB", (512, 512), (247, 248, 250))
    draw = ImageDraw.Draw(image)
    draw.line((80, 256, 432, 256), fill=(20, 60, 90), width=4)
    draw.rectangle((210, 246, 260, 266), fill=(40, 40, 44))
    image.save(image_path)

    generic = assess_render_quality(image_path, "generic prop")
    sword = assess_render_quality(image_path, "crystal sword")

    assert sword.score > generic.score
    assert all("mostly background" not in warning for warning in sword.warnings)
