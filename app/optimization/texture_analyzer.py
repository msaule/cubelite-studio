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
    production_score: int | None = None
    warnings: list[str] | None = None
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
            score, warnings = _score_texture(rgb.width, rgb.height, contrast, variance)
            return TextureStats(
                success=True,
                path=str(texture_path),
                width=rgb.width,
                height=rgb.height,
                file_size_mb=round(texture_path.stat().st_size / (1024 * 1024), 4),
                contrast_score=contrast,
                color_variance_score=variance,
                production_score=score,
                warnings=warnings,
            )
    except Exception as exc:
        return TextureStats(False, str(texture_path), error_message=f"Texture could not be analyzed: {exc}")


def _score_texture(width: int, height: int, contrast: float, variance: float) -> tuple[int, list[str]]:
    score = 100
    warnings: list[str] = []
    if width != height:
        score -= 15
        warnings.append("Texture is not square.")
    if min(width, height) < 512:
        score -= 12
        warnings.append("Texture is below 512px; use 1024px for portfolio-quality Roblox props.")
    if contrast < 0.18:
        score -= 20
        warnings.append("Texture has very low contrast and may read flat in Roblox Studio.")
    if variance < 0.08:
        score -= 16
        warnings.append("Texture has little color variation.")
    if contrast > 0.98 and variance > 0.28:
        score -= 10
        warnings.append("Texture is very busy; inspect seams and silhouettes before using it.")
    return max(0, min(100, score)), warnings
