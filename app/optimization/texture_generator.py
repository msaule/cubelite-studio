from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import math
import random
import time


@dataclass
class TextureResult:
    success: bool
    output_path: str | None
    provider: str
    description: str
    model_id: str | None = None
    elapsed_seconds: float | None = None
    device: str | None = None
    seed: int | None = None
    map_paths: dict[str, str] = field(default_factory=dict)
    quality_notes: list[str] = field(default_factory=list)
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


DEFAULT_DIFFUSERS_MODEL = "hf-internal-testing/tiny-stable-diffusion-pipe"
QUALITY_DIFFUSERS_MODEL = "stable-diffusion-v1-5/stable-diffusion-v1-5"
SUPPORTED_TEXTURE_PROVIDERS = {"studio", "procedural", "diffusers", "neural"}
MIN_TEXTURE_SIZE = 64
MAX_TEXTURE_SIZE = 2048


def generate_texture_atlas(
    prompt: str,
    output_png: Path,
    size: int = 1024,
    provider: str = "procedural",
    model_id: str | None = None,
    steps: int = 8,
    seed: int = 0,
) -> TextureResult:
    provider = provider.strip().lower()
    if provider not in SUPPORTED_TEXTURE_PROVIDERS:
        return TextureResult(False, None, provider, "", error_message=f"Unknown texture provider: {provider}")
    try:
        normalized_size = normalize_texture_size(size)
    except ValueError as exc:
        return TextureResult(False, None, provider, "", error_message=str(exc))

    if provider in {"diffusers", "neural"}:
        return _generate_diffusers_texture(prompt, output_png, normalized_size, model_id or DEFAULT_DIFFUSERS_MODEL, steps, seed)

    return _generate_studio_texture(prompt, output_png, normalized_size, provider, seed)


def generate_material_pack(
    prompt: str,
    output_dir: Path,
    size: int = 1024,
    provider: str = "studio",
    model_id: str | None = None,
    steps: int = 8,
    seed: int = 0,
) -> TextureResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    albedo_path = output_dir / "albedo.png"
    provider = provider.strip().lower()
    result = generate_texture_atlas(
        prompt,
        albedo_path,
        size=size,
        provider=provider,
        model_id=model_id,
        steps=steps,
        seed=seed,
    )
    if not result.success:
        return result

    material = infer_material(prompt)
    try:
        from PIL import Image
    except Exception as exc:
        result.success = False
        result.error_message = f"Pillow is required for material-map generation: {exc}"
        return result

    try:
        with Image.open(albedo_path) as image:
            albedo = image.convert("RGB")
            height = _height_from_albedo(albedo, material)
            normal_path = output_dir / "normal.png"
            roughness_path = output_dir / "roughness.png"
            metallic_path = output_dir / "metallic.png"
            _normal_from_height(height).save(normal_path)
            _roughness_map(albedo, material).save(roughness_path)
            _metallic_map(albedo.size, material).save(metallic_path)
            result.map_paths = {
                "albedo": str(albedo_path),
                "normal": str(normal_path),
                "roughness": str(roughness_path),
                "metallic": str(metallic_path),
            }
            result.quality_notes = _quality_notes_for_provider(provider)
            return result
    except Exception as exc:
        result.success = False
        result.error_message = f"Material pack generation failed: {exc}"
        return result


def _generate_studio_texture(
    prompt: str,
    output_png: Path,
    size: int,
    provider: str,
    seed: int,
) -> TextureResult:
    try:
        from PIL import Image, ImageDraw
    except Exception as exc:
        return TextureResult(False, None, provider, "", error_message=f"Pillow is required for texture generation: {exc}")

    started = time.perf_counter()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    material = infer_material(prompt)
    style = infer_style(prompt)
    rng = random.Random(seed or stable_prompt_seed(prompt))

    base, accent, line = _style_palette(material, style)
    image = Image.new("RGB", (size, size), base)
    draw = ImageDraw.Draw(image)
    _draw_noise(draw, size, rng, base, accent, density=2)

    if material == "wood":
        _draw_tileable_wood(draw, size, rng, line, accent)
    elif material == "metal":
        _draw_tileable_metal(draw, size, rng, line, accent)
    elif material == "crystal":
        _draw_tileable_crystal(draw, size, rng, line, accent)
    else:
        _draw_tileable_clay(draw, size, rng, line)
    if style == "toybox":
        _draw_toybox_accents(draw, size, rng, line, accent)
    elif style == "sci_fi":
        _draw_scifi_accents(draw, size, rng, line, accent)
    elif style == "fantasy":
        _draw_fantasy_accents(draw, size, rng, line, accent)

    image = _finish_game_texture(image, material, rng)
    image.save(output_png)
    return TextureResult(
        True,
        str(output_png),
        provider,
        f"Studio {style} {material} material atlas generated from prompt keywords.",
        elapsed_seconds=round(time.perf_counter() - started, 3),
        seed=seed,
        map_paths={"albedo": str(output_png)},
        quality_notes=_quality_notes_for_provider(provider),
    )


def normalize_texture_size(size: int) -> int:
    size = int(size)
    if size < MIN_TEXTURE_SIZE or size > MAX_TEXTURE_SIZE:
        raise ValueError(f"Texture size must be between {MIN_TEXTURE_SIZE} and {MAX_TEXTURE_SIZE}px.")
    if size % 8 != 0:
        size = max(MIN_TEXTURE_SIZE, (size // 8) * 8)
    return size


def stable_prompt_seed(prompt: str) -> int:
    value = 2166136261
    for char in prompt:
        value ^= ord(char)
        value = (value * 16777619) % (2**32)
    return value


def _generate_diffusers_texture(
    prompt: str,
    output_png: Path,
    size: int,
    model_id: str,
    steps: int,
    seed: int,
) -> TextureResult:
    started = time.perf_counter()
    try:
        import torch
        from diffusers import StableDiffusionPipeline
    except Exception as exc:
        return TextureResult(False, None, "diffusers", "", model_id=model_id, seed=seed, error_message=f"Diffusers is not installed or could not import: {exc}")

    try:
        output_png.parent.mkdir(parents=True, exist_ok=True)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32
        pipeline = StableDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=dtype,
            safety_checker=None,
            requires_safety_checker=False,
        )
        if hasattr(pipeline, "enable_attention_slicing"):
            pipeline.enable_attention_slicing()
        if hasattr(pipeline, "enable_vae_slicing"):
            pipeline.enable_vae_slicing()
        if device == "cuda" and hasattr(pipeline, "enable_model_cpu_offload"):
            pipeline.enable_model_cpu_offload()
        else:
            pipeline = pipeline.to(device)
        generator = torch.Generator(device=device).manual_seed(seed)
        texture_prompt = build_texture_prompt(prompt)
        with torch.inference_mode():
            image = pipeline(
                texture_prompt,
                negative_prompt="text, watermark, logo, blurry, photorealistic scene, character, background",
                num_inference_steps=max(1, int(steps)),
                guidance_scale=6.0,
                width=int(size),
                height=int(size),
                generator=generator,
            ).images[0]
        image.save(output_png)
        del pipeline
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return TextureResult(
            True,
            str(output_png),
            "diffusers",
            "Neural texture atlas generated with Diffusers. This is a 2D atlas provider, not a 3D-aware texturing model.",
            model_id=model_id,
            elapsed_seconds=round(time.perf_counter() - started, 3),
            device=device,
            seed=seed,
            map_paths={"albedo": str(output_png)},
            quality_notes=_quality_notes_for_provider("diffusers"),
        )
    except Exception as exc:
        return TextureResult(
            False,
            None,
            "diffusers",
            "",
            model_id=model_id,
            elapsed_seconds=round(time.perf_counter() - started, 3),
            seed=seed,
            error_message=f"Diffusers texture generation failed: {exc}",
        )


def build_texture_prompt(prompt: str) -> str:
    material = infer_material(prompt)
    cleaned = " ".join(prompt.split())[:55]
    return f"seamless stylized {material} game texture atlas, clean surface details, no text, {cleaned}"


def infer_material(prompt: str) -> str:
    lower = prompt.lower()
    if any(word in lower for word in ("crystal", "gem", "magic", "glowing")):
        return "crystal"
    if any(word in lower for word in ("wood", "crate", "chest", "boat", "barrel", "plank")):
        return "wood"
    if any(word in lower for word in ("sword", "shield", "metal", "robot")):
        return "metal"
    return "clay"


def infer_style(prompt: str) -> str:
    lower = prompt.lower()
    if any(word in lower for word in ("toy", "toybox", "friendly", "cute")):
        return "toybox"
    if any(word in lower for word in ("sci-fi", "scifi", "supply box", "hard-surface", "emissive")):
        return "sci_fi"
    if any(word in lower for word in ("fantasy", "magic", "medieval", "potion", "crystal")):
        return "fantasy"
    return "low_poly"


def _palette(material: str) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    return _style_palette(material, "low_poly")


def _style_palette(material: str, style: str) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    palettes = {
        ("low_poly", "wood"): ((126, 82, 45), (179, 116, 58), (72, 46, 27)),
        ("low_poly", "metal"): ((130, 134, 141), (190, 196, 205), (63, 67, 74)),
        ("low_poly", "crystal"): ((97, 78, 166), (107, 204, 216), (38, 31, 83)),
        ("low_poly", "clay"): ((137, 140, 130), (174, 177, 166), (82, 84, 78)),
        ("toybox", "wood"): ((209, 129, 65), (246, 175, 91), (111, 65, 40)),
        ("toybox", "metal"): ((114, 171, 205), (181, 224, 238), (54, 92, 130)),
        ("toybox", "crystal"): ((166, 92, 226), (110, 230, 228), (73, 40, 132)),
        ("toybox", "clay"): ((217, 104, 112), (255, 184, 91), (112, 71, 144)),
        ("sci_fi", "wood"): ((72, 83, 91), (126, 147, 156), (35, 43, 50)),
        ("sci_fi", "metal"): ((78, 88, 101), (167, 190, 205), (25, 31, 41)),
        ("sci_fi", "crystal"): ((35, 78, 115), (78, 231, 221), (11, 28, 46)),
        ("sci_fi", "clay"): ((72, 83, 91), (131, 149, 164), (28, 35, 46)),
        ("fantasy", "wood"): ((109, 68, 43), (194, 134, 69), (56, 34, 28)),
        ("fantasy", "metal"): ((112, 111, 125), (214, 184, 109), (50, 48, 61)),
        ("fantasy", "crystal"): ((81, 60, 156), (99, 225, 231), (32, 24, 90)),
        ("fantasy", "clay"): ((118, 112, 91), (188, 166, 104), (68, 60, 47)),
    }
    return palettes.get((style, material), palettes[("low_poly", "clay")])


def _draw_noise(draw, size: int, rng: random.Random, base, accent, density: int = 3) -> None:
    for _ in range(size * density):
        x = rng.randrange(size)
        y = rng.randrange(size)
        mix = rng.random()
        color = tuple(int(base[i] * (1 - mix) + accent[i] * mix) for i in range(3))
        draw.point((x, y), fill=color)


def _draw_tileable_wood(draw, size: int, rng: random.Random, line, accent) -> None:
    grain = _mix(accent, line, 0.22)
    highlight = _mix(accent, (255, 230, 180), 0.12)
    for y in range(0, size, max(18, size // 42)):
        offset = rng.randrange(-8, 9)
        points = []
        for x in range(0, size + 24, 24):
            wave = int(7 * math.sin((x / size) * math.tau * 2 + y * 0.013))
            points.append((x, y + offset + wave))
        draw.line(points, fill=grain, width=max(1, size // 520))
    for _ in range(max(12, size // 36)):
        x = rng.randrange(size)
        y = rng.randrange(size)
        rx = rng.randrange(max(5, size // 150), max(8, size // 82))
        ry = max(3, rx // 2)
        draw.ellipse((x - rx, y - ry, x + rx, y + ry), outline=_mix(line, accent, 0.35), width=1)
    for x in range(0, size, max(96, size // 7)):
        draw.line((x, 0, x, size), fill=_mix(line, accent, 0.38), width=max(1, size // 420))
        draw.line((x + 2, 0, x + 2, size), fill=highlight, width=1)


def _draw_tileable_metal(draw, size: int, rng: random.Random, line, accent) -> None:
    panel = _mix(line, accent, 0.36)
    for pos in range(0, size, max(96, size // 6)):
        draw.line((pos, 0, pos, size), fill=panel, width=max(1, size // 420))
        draw.line((0, pos, size, pos), fill=panel, width=max(1, size // 420))
    for offset in range(-size, size * 2, max(68, size // 9)):
        draw.line((offset, 0, offset - size // 2, size), fill=_mix(accent, (255, 255, 255), 0.1), width=1)
    for _ in range(max(10, size // 80)):
        x = rng.randrange(size)
        y = rng.randrange(size)
        w = rng.randrange(max(22, size // 40), max(40, size // 18))
        h = max(4, size // 110)
        draw.rectangle((x, y, min(size - 1, x + w), min(size - 1, y + h)), fill=_mix(accent, (180, 255, 250), 0.28), outline=line)


def _draw_tileable_crystal(draw, size: int, rng: random.Random, line, accent) -> None:
    for _ in range(max(20, size // 26)):
        cx = rng.randrange(size)
        cy = rng.randrange(size)
        radius = rng.randrange(size // 22, size // 9)
        color = _mix(accent, (120, 245, 245), rng.uniform(0.3, 0.62))
        points = [
            (cx, cy - radius),
            (cx + radius // 2, cy),
            (cx, cy + radius),
            (cx - radius // 2, cy),
        ]
        draw.polygon(points, outline=line, fill=color)
        draw.line((cx - radius // 3, cy, cx + radius // 3, cy), fill=_mix(color, (255, 255, 255), 0.35), width=1)


def _draw_tileable_clay(draw, size: int, rng: random.Random, line) -> None:
    step = max(72, size // 8)
    for pos in range(0, size, step):
        draw.line((pos, 0, pos, size), fill=line, width=1)
        draw.line((0, pos, size, pos), fill=line, width=1)
    for _ in range(size // 8):
        x = rng.randrange(size)
        y = rng.randrange(size)
        draw.point((x, y), fill=_mix(line, (255, 255, 255), 0.18))


def _draw_wood(draw, size: int, rng: random.Random, line, accent) -> None:
    plank_w = max(96, size // 5)
    seam_w = max(4, size // 160)
    highlight = _mix(accent, (255, 235, 190), 0.24)
    shadow = _mix(line, (0, 0, 0), 0.24)
    for index, x in enumerate(range(0, size + plank_w, plank_w)):
        seam_x = x + rng.randrange(-max(2, plank_w // 16), max(3, plank_w // 16))
        draw.rectangle((seam_x - seam_w, 0, seam_x + seam_w, size), fill=shadow)
        draw.line((seam_x + seam_w + 2, 0, seam_x + seam_w + 2, size), fill=highlight, width=max(1, seam_w // 2))
        x0 = max(0, x)
        x1 = min(size, x + plank_w)
        if x1 <= x0:
            continue
        draw.rectangle((x0 + 8, 8, max(x0 + 8, x1 - 8), size - 8), outline=_mix(line, accent, 0.42), width=max(2, size // 360))
        for nail_y in (max(28, size // 18), size - max(28, size // 18)):
            nail_x = min(max(x0 + plank_w // 2 + rng.randrange(-10, 11), 12), size - 12)
            radius = max(3, size // 180)
            draw.ellipse((nail_x - radius, nail_y - radius, nail_x + radius, nail_y + radius), fill=_mix(line, (0, 0, 0), 0.3))
            draw.ellipse((nail_x - radius // 2, nail_y - radius // 2, nail_x, nail_y), fill=_mix(highlight, (255, 255, 255), 0.15))
        for _ in range(2):
            knot_x = rng.randrange(x0 + 18, max(x0 + 19, x1 - 18))
            knot_y = rng.randrange(48, max(49, size - 48))
            rx = rng.randrange(max(9, size // 90), max(14, size // 50))
            ry = max(6, rx // 2)
            draw.ellipse((knot_x - rx, knot_y - ry, knot_x + rx, knot_y + ry), outline=_mix(line, (0, 0, 0), 0.15), width=max(1, size // 360))
            draw.arc((knot_x - rx + 4, knot_y - ry + 2, knot_x + rx - 4, knot_y + ry - 2), 0, 320, fill=_mix(accent, (255, 220, 160), 0.2), width=max(1, size // 430))
        for y in range(rng.randrange(20, 60), size, max(58, size // 12)):
            wobble = rng.randrange(2, max(4, size // 90))
            points = [(px, y + int(rng.uniform(-wobble, wobble))) for px in range(max(0, x), min(size, x + plank_w) + 1, 48)]
            if len(points) > 1:
                draw.line(points, fill=_mix(accent, line, 0.28), width=max(1, size // 320))
        if index % 2 == 1:
            if x1 >= x0:
                draw.rectangle((x0, 0, x1, size), outline=_mix(line, accent, 0.4), width=max(1, size // 400))


def _draw_metal(draw, size: int, line, accent) -> None:
    for offset in range(-size, size * 2, max(44, size // 10)):
        draw.line((offset, 0, offset - size, size), fill=_mix(accent, (255, 255, 255), 0.18), width=max(2, size // 320))
    margin = size // 12
    draw.rectangle((margin, margin, size - margin, size - margin), outline=line, width=max(4, size // 180))
    for x in range(margin * 2, size - margin, max(96, size // 5)):
        draw.ellipse((x - 8, margin - 8, x + 8, margin + 8), fill=_mix(line, (0, 0, 0), 0.2))
        draw.ellipse((x - 8, size - margin - 8, x + 8, size - margin + 8), fill=_mix(line, (0, 0, 0), 0.2))


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


def _draw_toybox_accents(draw, size: int, rng: random.Random, line, accent) -> None:
    for _ in range(18):
        x = rng.randrange(size)
        y = rng.randrange(size)
        radius = rng.randrange(max(8, size // 90), max(16, size // 38))
        color = _mix(accent, (255, 255, 255), rng.uniform(0.12, 0.34))
        draw.rounded_rectangle((x - radius, y - radius // 2, x + radius, y + radius // 2), radius=radius // 2, fill=color, outline=_mix(line, color, 0.2), width=max(1, size // 420))


def _draw_scifi_accents(draw, size: int, rng: random.Random, line, accent) -> None:
    glow = _mix(accent, (80, 255, 235), 0.45)
    for _ in range(10):
        x = rng.randrange(20, max(21, size - 80))
        y = rng.randrange(20, max(21, size - 60))
        w = rng.randrange(max(44, size // 12), max(72, size // 5))
        h = rng.randrange(max(10, size // 80), max(18, size // 40))
        draw.rectangle((x, y, min(size - 1, x + w), min(size - 1, y + h)), fill=glow, outline=line, width=max(1, size // 360))
    for x in range(0, size, max(128, size // 6)):
        draw.line((x, 0, x + size // 3, size), fill=_mix(line, accent, 0.25), width=max(1, size // 360))


def _draw_fantasy_accents(draw, size: int, rng: random.Random, line, accent) -> None:
    gold = (216, 165, 77)
    for _ in range(14):
        x = rng.randrange(size)
        y = rng.randrange(size)
        r = rng.randrange(max(6, size // 120), max(13, size // 58))
        draw.polygon([(x, y - r), (x + r, y), (x, y + r), (x - r, y)], fill=_mix(accent, gold, 0.35), outline=line)
    for y in range(size // 8, size, max(128, size // 5)):
        draw.line((0, y, size, y + rng.randrange(-20, 21)), fill=_mix(line, gold, 0.28), width=max(1, size // 300))


def _finish_game_texture(image, material: str, rng: random.Random):
    from PIL import ImageDraw, ImageEnhance, ImageFilter

    size = image.width
    image = image.filter(ImageFilter.GaussianBlur(radius=0.18))
    overlay = ImageDraw.Draw(image, "RGBA")
    vignette_width = max(10, size // 48)
    for offset in range(vignette_width):
        alpha = int(42 * (1 - offset / vignette_width))
        overlay.rectangle((offset, offset, size - offset - 1, size - offset - 1), outline=(0, 0, 0, alpha))
    if material == "crystal":
        for _ in range(12):
            x0 = rng.randrange(size)
            y0 = rng.randrange(size)
            overlay.line((x0, y0, min(size, x0 + rng.randrange(40, 160)), max(0, y0 - rng.randrange(40, 160))), fill=(210, 255, 255, 90), width=max(2, size // 220))
    image = ImageEnhance.Contrast(image).enhance(1.08)
    image = ImageEnhance.Color(image).enhance(1.04)
    return image


def _height_from_albedo(albedo, material: str):
    from PIL import ImageEnhance, ImageFilter

    gray = albedo.convert("L")
    if material == "metal":
        gray = ImageEnhance.Contrast(gray).enhance(0.55)
    elif material == "wood":
        gray = ImageEnhance.Contrast(gray).enhance(1.35)
    else:
        gray = ImageEnhance.Contrast(gray).enhance(1.1)
    return gray.filter(ImageFilter.GaussianBlur(radius=0.7))


def _normal_from_height(height):
    from PIL import Image

    width, height_px = height.size
    pixels = height.load()
    normal = Image.new("RGB", (width, height_px), (128, 128, 255))
    out = normal.load()
    strength = 3.4
    for y in range(height_px):
        ym = max(0, y - 1)
        yp = min(height_px - 1, y + 1)
        for x in range(width):
            xm = max(0, x - 1)
            xp = min(width - 1, x + 1)
            dx = (pixels[xp, y] - pixels[xm, y]) / 255.0
            dy = (pixels[x, yp] - pixels[x, ym]) / 255.0
            nx = -dx * strength
            ny = -dy * strength
            nz = 1.0
            length = max((nx * nx + ny * ny + nz * nz) ** 0.5, 1e-6)
            out[x, y] = (
                int((nx / length * 0.5 + 0.5) * 255),
                int((ny / length * 0.5 + 0.5) * 255),
                int((nz / length * 0.5 + 0.5) * 255),
            )
    return normal


def _roughness_map(albedo, material: str):
    from PIL import Image, ImageEnhance

    base_values = {"wood": 185, "metal": 96, "crystal": 62, "clay": 210}
    roughness = Image.new("L", albedo.size, base_values.get(material, 190))
    detail = albedo.convert("L")
    detail = ImageEnhance.Contrast(detail).enhance(0.35)
    return Image.blend(roughness, detail, 0.24)


def _metallic_map(size: tuple[int, int], material: str):
    from PIL import Image

    value = 220 if material == "metal" else 0
    return Image.new("L", size, value)


def _quality_notes_for_provider(provider: str) -> list[str]:
    if provider in {"diffusers", "neural"}:
        return [
            "Experimental 2D atlas provider; inspect seams and semantic placement before Roblox use.",
            "For production props, compare against the studio material provider and multi-angle textured renders.",
        ]
    return [
        "Clean repeatable material atlas designed for low-poly Roblox props.",
        "Includes derived normal, roughness, and metallic maps for manual material setup when supported.",
    ]


def _mix(a, b, amount: float) -> tuple[int, int, int]:
    return tuple(int(a[i] * (1 - amount) + b[i] * amount) for i in range(3))
