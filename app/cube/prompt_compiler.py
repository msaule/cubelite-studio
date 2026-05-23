from __future__ import annotations


SWORD_ASSET_SPEC = (
    "single centered fantasy sword game asset, one complete object, vertical long thin silhouette, "
    "faceted cyan crystal blade with sharp pointed tip, dark metal handle, gold crossguard, wrapped grip, "
    "green gem in the guard, low poly stylized Roblox prop, clean topology, readable bevels, no base, "
    "no background, no character, no duplicate swords, no floating fragments"
)


def compile_asset_prompt(prompt: str, style_name: str | None = None) -> str:
    base = " ".join(prompt.split())
    lower = base.lower()
    if "sword" in lower:
        return _merge_prompt(base, SWORD_ASSET_SPEC)
    return base


def infer_asset_bbox(prompt: str) -> tuple[float, float, float] | None:
    lower = prompt.lower()
    if "sword" in lower:
        return (0.34, 2.55, 0.18)
    if "sign" in lower and "post" in lower:
        return (0.90, 1.65, 0.18)
    if "crate" in lower:
        return (1.0, 1.0, 1.0)
    if "chest" in lower:
        return (1.45, 0.80, 0.95)
    if "barrel" in lower:
        return (0.85, 1.15, 0.85)
    return None


def _merge_prompt(base: str, asset_spec: str) -> str:
    lower = base.lower()
    additions = [term.strip() for term in asset_spec.split(",") if term.strip() and term.strip().lower() not in lower]
    if not additions:
        return base
    return f"{base}, {', '.join(additions)}"
