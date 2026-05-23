from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import random


@dataclass
class TextureResult:
    success: bool
    output_path: str | None
    provider: str
    description: str
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def generate_texture_atlas(prompt: str, output_png: Path, size: int = 1024, provider: str = "procedural") -> TextureResult:
    if provider != "procedural":
        return TextureResult(
            False,
            None,
            provider,
            "",
            "Only the procedural texture provider is implemented. A neural texture model can plug into this interface later.",
        )

    try:
        from PIL import Image, ImageDraw, ImageFilter
    except Exception as exc:
        return TextureResult(False, None, provider, "", f"Pillow is required for texture generation: {exc}")

    output_png.parent.mkdir(parents=True, exist_ok=True)
    material = infer_material(prompt)
    rng = random.Random(abs(hash(prompt)) % (2**32))

    base, accent, line = _palette(material)
    image = Image.new("RGB", (size, size), base)
    draw = ImageDraw.Draw(image)
    _draw_noise(draw, size, rng, base, accent)

    if material == "wood":
        _draw_wood(draw, size, rng, line, accent)
    elif material == "metal":
        _draw_metal(draw, size, line, accent)
    elif material == "crystal":
        _draw_crystal(draw, size, rng, line, accent)
    else:
        _draw_clay_grid(draw, size, line)

    image = image.filter(ImageFilter.GaussianBlur(radius=0.25))
    image.save(output_png)
    return TextureResult(True, str(output_png), provider, f"Procedural {material} atlas generated from prompt keywords.")


def infer_material(prompt: str) -> str:
    lower = prompt.lower()
    if any(word in lower for word in ("wood", "crate", "chest", "boat", "barrel", "plank")):
        return "wood"
    if any(word in lower for word in ("sword", "shield", "metal", "robot")):
        return "metal"
    if any(word in lower for word in ("crystal", "gem", "magic", "glowing")):
        return "crystal"
    return "clay"


def _palette(material: str) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    palettes = {
        "wood": ((126, 82, 45), (179, 116, 58), (72, 46, 27)),
        "metal": ((130, 134, 141), (190, 196, 205), (63, 67, 74)),
        "crystal": ((97, 78, 166), (107, 204, 216), (38, 31, 83)),
        "clay": ((137, 140, 130), (174, 177, 166), (82, 84, 78)),
    }
    return palettes.get(material, palettes["clay"])


def _draw_noise(draw, size: int, rng: random.Random, base, accent) -> None:
    for _ in range(size * 5):
        x = rng.randrange(size)
        y = rng.randrange(size)
        mix = rng.random()
        color = tuple(int(base[i] * (1 - mix) + accent[i] * mix) for i in range(3))
        draw.point((x, y), fill=color)


def _draw_wood(draw, size: int, rng: random.Random, line, accent) -> None:
    step = max(64, size // 8)
    for x in range(0, size, step):
        draw.line((x, 0, x, size), fill=line, width=max(3, size // 220))
    for y in range(step // 2, size, step):
        draw.line((0, y, size, y), fill=line, width=max(2, size // 260))
    for _ in range(24):
        y = rng.randrange(size)
        wobble = rng.randrange(8, 24)
        points = [(x, y + int(rng.uniform(-wobble, wobble))) for x in range(0, size + 1, 64)]
        draw.line(points, fill=accent, width=2)


def _draw_metal(draw, size: int, line, accent) -> None:
    for offset in range(-size, size * 2, max(40, size // 12)):
        draw.line((offset, 0, offset - size, size), fill=accent, width=2)
    margin = size // 12
    draw.rectangle((margin, margin, size - margin, size - margin), outline=line, width=max(4, size // 180))


def _draw_crystal(draw, size: int, rng: random.Random, line, accent) -> None:
    for _ in range(18):
        cx = rng.randrange(size)
        cy = rng.randrange(size)
        radius = rng.randrange(size // 14, size // 6)
        points = [
            (cx, cy - radius),
            (cx + radius // 2, cy),
            (cx, cy + radius),
            (cx - radius // 2, cy),
        ]
        draw.polygon(points, outline=line, fill=accent)


def _draw_clay_grid(draw, size: int, line) -> None:
    step = max(64, size // 8)
    for pos in range(0, size, step):
        draw.line((pos, 0, pos, size), fill=line, width=1)
        draw.line((0, pos, size, pos), fill=line, width=1)

