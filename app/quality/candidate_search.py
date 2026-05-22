from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from app.benchmark.benchmark_runner import run_single_pipeline
from app.config import OUTPUTS_DIR, REPORTS_DIR
from app.cube.low_vram_profiles import GenerationProfile, get_profile
from app.utils.time_utils import utc_timestamp


@dataclass(frozen=True)
class CandidateSearchConfig:
    prompt: str
    profile_name: str = "6GB Quality"
    seeds: tuple[int, ...] = (11, 23, 37)
    top_p_values: tuple[float | None, ...] = (0.9,)
    guidance_scales: tuple[float, ...] = (1.0,)
    target_face_count: int = 16000
    dry_run: bool = False


@dataclass
class CandidateResult:
    prompt: str
    profile: str
    seed: int | None
    top_p: float | None
    guidance_scale: float
    success: bool
    quality_score: float
    readiness_score: int | None
    triangle_count: int | None
    peak_vram_gb: float | None
    generation_time_seconds: float
    output_path: str | None
    error_message: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class CandidateSearchResult:
    prompt: str
    candidates: list[CandidateResult]
    best_candidate: CandidateResult | None
    json_path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "prompt": self.prompt,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "best_candidate": self.best_candidate.to_dict() if self.best_candidate else None,
            "json_path": self.json_path,
        }


def score_candidate(row_dict: dict[str, object], details: dict[str, object]) -> float:
    """Score a generated candidate for curation.

    This is deliberately not a visual-quality oracle. It ranks candidates that
    are structurally more likely to survive a Roblox import pass, then leaves
    final selection to human inspection using render plates.
    """
    if not row_dict.get("success"):
        return 0.0

    readiness = float(row_dict.get("readiness_score") or 0)
    mesh_stats = details.get("optimized_mesh_stats") or details.get("mesh_stats") or {}
    triangle_count = int(mesh_stats.get("triangle_count") or 0)
    file_size_mb = float(mesh_stats.get("file_size_mb") or 0)
    warnings = mesh_stats.get("warnings") or []

    score = readiness
    if 1_000 <= triangle_count <= 25_000:
        score += 12
    elif triangle_count > 40_000:
        score -= 20
    elif triangle_count < 250:
        score -= 10

    if file_size_mb <= 10:
        score += 5
    elif file_size_mb > 30:
        score -= 10

    if warnings:
        score -= min(12, 3 * len(warnings))

    simplification = details.get("simplification") or {}
    if simplification and not simplification.get("success"):
        score -= 12

    return round(max(score, 0.0), 2)


def run_candidate_search(
    config: CandidateSearchConfig,
    cube_repo_path: Path | str | None,
    model_weights_path: Path | str | None,
    outputs_dir: Path = OUTPUTS_DIR,
    reports_dir: Path = REPORTS_DIR,
) -> CandidateSearchResult:
    base_profile = get_profile(config.profile_name)
    candidates: list[CandidateResult] = []

    for seed in config.seeds:
        for top_p in config.top_p_values:
            for guidance_scale in config.guidance_scales:
                profile: GenerationProfile = replace(
                    base_profile,
                    top_p=top_p,
                    guidance_scale=guidance_scale,
                    random_seed=seed,
                    target_face_count=config.target_face_count,
                )
                row, details = run_single_pipeline(
                    prompt=config.prompt,
                    profile=profile,
                    cube_repo_path=cube_repo_path,
                    model_weights_path=model_weights_path,
                    outputs_dir=outputs_dir,
                    dry_run=config.dry_run,
                    package_export=True,
                    simplify=True,
                )
                row_dict = row.to_dict()
                mesh_stats = details.get("optimized_mesh_stats") or details.get("mesh_stats") or {}
                candidates.append(
                    CandidateResult(
                        prompt=config.prompt,
                        profile=profile.name,
                        seed=seed,
                        top_p=top_p,
                        guidance_scale=guidance_scale,
                        success=bool(row.success),
                        quality_score=score_candidate(row_dict, details),
                        readiness_score=row.readiness_score,
                        triangle_count=mesh_stats.get("triangle_count") if isinstance(mesh_stats, dict) else None,
                        peak_vram_gb=row.peak_vram_gb,
                        generation_time_seconds=row.generation_time_seconds,
                        output_path=row.output_path,
                        error_message=row.error_message,
                    )
                )

    best = max(candidates, key=lambda candidate: candidate.quality_score, default=None)
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"quality-search-{utc_timestamp()}.json"
    result = CandidateSearchResult(
        prompt=config.prompt,
        candidates=candidates,
        best_candidate=best,
        json_path=str(json_path),
    )
    json_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    return result

