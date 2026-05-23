from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class RenderQualityReport:
    score: float
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, float | int | str | None] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def assess_render_quality(render_path: str | Path | None) -> RenderQualityReport:
    if not render_path:
        return RenderQualityReport(50.0, ["No render plate was available for visual scoring."], {})
    path = Path(render_path)
    if not path.exists():
        return RenderQualityReport(45.0, ["Render plate path does not exist."], {"path": str(path)})
    try:
        from PIL import Image, ImageFilter, ImageStat
    except Exception as exc:
        return RenderQualityReport(50.0, [f"Pillow is required for render scoring: {exc}"], {"path": str(path)})

    try:
        with Image.open(path) as image:
            gray = image.convert("L").resize((256, 256))
            stat = ImageStat.Stat(gray)
            mean = float(stat.mean[0])
            stddev = float(stat.stddev[0])
            edges = gray.filter(ImageFilter.FIND_EDGES)
            edge_stat = ImageStat.Stat(edges)
            edge_strength = float(edge_stat.mean[0]) / 255.0
            background_like = _background_like_ratio(gray)
            score = 70.0
            warnings: list[str] = []
            if stddev < 18:
                score -= 18
                warnings.append("Render plate has low contrast; the silhouette may be weak.")
            else:
                score += min(10, stddev / 8)
            if edge_strength < 0.035:
                score -= 18
                warnings.append("Render plate has little edge detail; geometry may be too simple or too flat.")
            elif edge_strength > 0.19:
                score -= 8
                warnings.append("Render plate is visually noisy; inspect for fragmented geometry.")
            else:
                score += 8
            if background_like > 0.92:
                score -= 15
                warnings.append("Render plate appears mostly background; object may be tiny or missing.")
            if mean < 35 or mean > 235:
                score -= 8
                warnings.append("Render plate exposure is extreme; visual review may be unreliable.")
            return RenderQualityReport(
                score=round(max(0.0, min(100.0, score)), 2),
                warnings=warnings,
                metrics={
                    "path": str(path),
                    "grayscale_mean": round(mean, 3),
                    "grayscale_stddev": round(stddev, 3),
                    "edge_strength": round(edge_strength, 4),
                    "background_like_ratio": round(background_like, 4),
                },
            )
    except Exception as exc:
        return RenderQualityReport(45.0, [f"Render plate could not be scored: {exc}"], {"path": str(path)})


def _background_like_ratio(gray_image) -> float:
    pixels = gray_image.getdata()
    count = 0
    total = gray_image.width * gray_image.height
    for value in pixels:
        if 232 <= value <= 252:
            count += 1
    return count / max(total, 1)
