from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class TextureStats:
    success: bool
    path: str
    width: int | None = None
    height: int | None = None
    file_size_mb: float | None = None
    contrast_score: float | None = None
    color_variance_score: float | None = None
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def analyze_texture(texture_path: Path) -> TextureStats:
    if not texture_path.exists():
        return TextureStats(False, str(texture_path), error_message="Texture file was not found.")
    try:
        from PIL import Image, ImageStat
    except Exception as exc:
        return TextureStats(False, str(texture_path), error_message=f"Pillow is required for texture analysis: {exc}")

    try:
        with Image.open(texture_path) as image:
            rgb = image.convert("RGB")
            stat = ImageStat.Stat(rgb)
            channel_stddev = [float(value) for value in stat.stddev]
            channel_range = []
            extrema = rgb.getextrema()
            for low, high in extrema:
                channel_range.append(float(high - low))
            contrast = round(sum(channel_range) / (3 * 255), 4)
            variance = round(sum(channel_stddev) / (3 * 128), 4)
            return TextureStats(
                success=True,
                path=str(texture_path),
                width=rgb.width,
                height=rgb.height,
                file_size_mb=round(texture_path.stat().st_size / (1024 * 1024), 4),
                contrast_score=contrast,
                color_variance_score=variance,
            )
    except Exception as exc:
        return TextureStats(False, str(texture_path), error_message=f"Texture could not be analyzed: {exc}")
