from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class GenerationProfile:
    name: str
    description: str
    target_vram_gb: str
    fast_inference: bool
    resolution_base: float
    use_fp16: bool
    enable_cpu_offload: bool
    generate_preview: bool
    simplify_after_generation: bool
    target_face_count: int
    notes: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


PROFILES: dict[str, GenerationProfile] = {
    "Auto": GenerationProfile(
        name="Auto",
        description="Selects a conservative profile based on detected VRAM.",
        target_vram_gb="Detected",
        fast_inference=False,
        resolution_base=4.0,
        use_fp16=True,
        enable_cpu_offload=True,
        generate_preview=False,
        simplify_after_generation=True,
        target_face_count=10000,
        notes="Auto is resolved before generation and does not imply unsupported Cube 3D flags.",
    ),
    "Low VRAM": GenerationProfile(
        name="Low VRAM",
        description="Experimental low-VRAM workflow for 6GB to 8GB GPUs.",
        target_vram_gb="6-8",
        fast_inference=False,
        resolution_base=4.0,
        use_fp16=True,
        enable_cpu_offload=True,
        generate_preview=False,
        simplify_after_generation=True,
        target_face_count=10000,
        notes="Prioritizes completing generations over detail. Preview generation is disabled by default.",
    ),
    "Balanced": GenerationProfile(
        name="Balanced",
        description="Middle-ground profile for 8GB to 12GB GPUs.",
        target_vram_gb="8-12",
        fast_inference=False,
        resolution_base=6.0,
        use_fp16=True,
        enable_cpu_offload=False,
        generate_preview=True,
        simplify_after_generation=True,
        target_face_count=18000,
        notes="Designed for practical creator iteration with moderate mesh complexity.",
    ),
    "High Quality": GenerationProfile(
        name="High Quality",
        description="Higher-detail profile for 16GB+ GPUs.",
        target_vram_gb="16+",
        fast_inference=True,
        resolution_base=8.0,
        use_fp16=True,
        enable_cpu_offload=False,
        generate_preview=True,
        simplify_after_generation=False,
        target_face_count=30000,
        notes="Fast inference may require more VRAM and depends on the detected Cube 3D installation.",
    ),
    "Benchmark Safe": GenerationProfile(
        name="Benchmark Safe",
        description="Very conservative profile intended to complete on modest hardware.",
        target_vram_gb="Minimum practical",
        fast_inference=False,
        resolution_base=4.0,
        use_fp16=True,
        enable_cpu_offload=True,
        generate_preview=False,
        simplify_after_generation=True,
        target_face_count=8000,
        notes="Useful for measuring the lowest workable path before trying heavier settings.",
    ),
}


def get_profile(name: str) -> GenerationProfile:
    return PROFILES.get(name, PROFILES["Auto"])


def recommend_profile(total_vram_gb: float | None) -> GenerationProfile:
    if total_vram_gb is None or total_vram_gb <= 0:
        return PROFILES["Benchmark Safe"]
    if total_vram_gb < 10:
        return PROFILES["Low VRAM"]
    if total_vram_gb < 16:
        return PROFILES["Balanced"]
    return PROFILES["High Quality"]


def resolve_auto_profile(profile: GenerationProfile, total_vram_gb: float | None) -> GenerationProfile:
    if profile.name == "Auto":
        return recommend_profile(total_vram_gb)
    return profile
