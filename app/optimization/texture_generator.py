from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
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
    rng = random.Random(seed or stable_prompt_seed(prompt))

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

    image = _finish_game_texture(image, material, rng)
    image.save(output_png)
    return TextureResult(
        True,
        str(output_png),
        provider,
        f"Studio {material} material atlas generated from prompt keywords.",
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
    for _ in range(size * 3):
        x = rng.randrange(size)
        y = rng.randrange(size)
        mix = rng.random()
        color = tuple(int(base[i] * (1 - mix) + accent[i] * mix) for i in range(3))
        draw.point((x, y), fill=color)


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
