from __future__ import annotations

from dataclasses import asdict, dataclass
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
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


DEFAULT_DIFFUSERS_MODEL = "hf-internal-testing/tiny-stable-diffusion-pipe"
QUALITY_DIFFUSERS_MODEL = "stable-diffusion-v1-5/stable-diffusion-v1-5"
SUPPORTED_TEXTURE_PROVIDERS = {"procedural", "diffusers", "neural"}
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

    try:
        from PIL import Image, ImageDraw, ImageFilter
    except Exception as exc:
        return TextureResult(False, None, provider, "", error_message=f"Pillow is required for texture generation: {exc}")

    started = time.perf_counter()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    material = infer_material(prompt)
    rng = random.Random(seed or stable_prompt_seed(prompt))

    base, accent, line = _palette(material)
    image = Image.new("RGB", (normalized_size, normalized_size), base)
    draw = ImageDraw.Draw(image)
    _draw_noise(draw, normalized_size, rng, base, accent)

    if material == "wood":
        _draw_wood(draw, normalized_size, rng, line, accent)
    elif material == "metal":
        _draw_metal(draw, normalized_size, line, accent)
    elif material == "crystal":
        _draw_crystal(draw, normalized_size, rng, line, accent)
    else:
        _draw_clay_grid(draw, normalized_size, line)

    image = image.filter(ImageFilter.GaussianBlur(radius=0.25))
    image.save(output_png)
    return TextureResult(
        True,
        str(output_png),
        provider,
        f"Procedural {material} atlas generated from prompt keywords.",
        elapsed_seconds=round(time.perf_counter() - started, 3),
        seed=seed,
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
