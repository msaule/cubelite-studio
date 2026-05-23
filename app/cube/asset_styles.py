from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AssetStyle:
    name: str
    description: str
    prompt_terms: tuple[str, ...]
    material_terms: tuple[str, ...]
    avoid_terms: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


STYLE_PRESETS: dict[str, AssetStyle] = {
    "Roblox Low Poly": AssetStyle(
        name="Roblox Low Poly",
        description="Clean blocky shapes with simple surfaces for fast Roblox import tests.",
        prompt_terms=("low poly", "single object", "clean silhouette", "simple readable geometry", "game prop"),
        material_terms=("flat color blocks", "subtle bevel shading", "clean stylized material"),
        avoid_terms=("full scene", "tiny details", "photorealistic", "thousands of parts"),
    ),
    "Toybox": AssetStyle(
        name="Toybox",
        description="Rounded, bright, plastic-like toy props.",
        prompt_terms=("toy-like proportions", "rounded chunky shapes", "single object", "friendly stylized prop"),
        material_terms=("soft plastic color", "painted edges", "smooth highlights"),
        avoid_terms=("gritty", "photorealistic", "sharp clutter", "complex background"),
    ),
    "Hand Painted Fantasy": AssetStyle(
        name="Hand Painted Fantasy",
        description="Readable fantasy props with painterly wood, metal, crystal, and cloth cues.",
        prompt_terms=("hand painted fantasy game asset", "single object", "clear silhouette", "simple decorative accents"),
        material_terms=("painted highlights", "warm shadows", "stylized fantasy material"),
        avoid_terms=("realistic dirt", "micro detail", "full environment", "many small ornaments"),
    ),
    "Sci-Fi Plastic": AssetStyle(
        name="Sci-Fi Plastic",
        description="Clean panels, simple vents, and stylized hard-surface props.",
        prompt_terms=("sci-fi game prop", "single object", "chunky hard-surface panels", "clean silhouette"),
        material_terms=("plastic panels", "simple emissive accents", "clean hard-surface lines"),
        avoid_terms=("dense greebles", "tiny wires", "photorealistic scratches", "full room"),
    ),
    "Medieval Wood Metal": AssetStyle(
        name="Medieval Wood Metal",
        description="Readable wood planks, bands, rivets, shields, crates, and chests.",
        prompt_terms=("medieval game prop", "single object", "wood and metal construction", "clear silhouette"),
        material_terms=("wood grain", "metal bands", "painted rivets", "warm stylized shading"),
        avoid_terms=("ultra detailed", "full scene", "cloth simulation", "tiny carvings everywhere"),
    ),
    "Crystal Magic": AssetStyle(
        name="Crystal Magic",
        description="Stylized gems, crystals, potions, and magical props.",
        prompt_terms=("stylized magical prop", "single object", "faceted shapes", "clear silhouette"),
        material_terms=("crystal facets", "glow accents", "cool highlights", "clean fantasy material"),
        avoid_terms=("particle effects", "full spell scene", "fog", "photorealistic"),
    ),
}


def style_names() -> list[str]:
    return list(STYLE_PRESETS.keys())


def get_style(name: str | None) -> AssetStyle:
    if not name:
        return STYLE_PRESETS["Roblox Low Poly"]
    return STYLE_PRESETS.get(name, STYLE_PRESETS["Roblox Low Poly"])


def strengthen_prompt(prompt: str, style_name: str | None = None) -> str:
    base = " ".join(prompt.split())
    style = get_style(style_name)
    lower = base.lower()
    additions = [term for term in style.prompt_terms if term.lower() not in lower]
    avoid = ", ".join(style.avoid_terms)
    return f"{base}, {', '.join(additions)}, avoid: {avoid}"
