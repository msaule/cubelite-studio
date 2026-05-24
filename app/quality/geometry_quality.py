from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class GeometryQualityReport:
    score: float
    status: str
    warnings: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    metrics: dict[str, float | int | str | None] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def assess_geometry_quality(prompt: str, mesh_stats: dict[str, object] | None) -> GeometryQualityReport:
    if not mesh_stats or not mesh_stats.get("success"):
        return GeometryQualityReport(
            score=0.0,
            status="reject",
            warnings=["Mesh failed to load; reject this candidate."],
            metrics={},
        )

    score = 72.0
    warnings: list[str] = []
    strengths: list[str] = []
    triangle_count = _int(mesh_stats.get("triangle_count"))
    file_size_mb = _float(mesh_stats.get("file_size_mb"))
    object_count = _int(mesh_stats.get("object_count"))
    bbox = _bbox(mesh_stats.get("bounding_box_dimensions"))
    archetype = _prompt_archetype(prompt)
    aspect_ratio = None
    flatness_ratio = None

    if 1_000 <= triangle_count <= 20_000:
        score += 12
        strengths.append("Triangle count is in a practical Roblox prop range.")
    elif 300 <= triangle_count < 1_000:
        score += 3
        warnings.append("Mesh is very simple; check whether the silhouette has enough shape.")
    elif triangle_count < 300:
        score -= 22
        warnings.append("Mesh is likely too simple to be a portfolio-quality asset.")
    elif triangle_count <= 35_000:
        score -= 6
        warnings.append("Mesh is somewhat heavy; simplification/import testing matters.")
    else:
        score -= 26
        warnings.append("Mesh is too heavy for a clean Roblox prop workflow.")

    if file_size_mb <= 8:
        score += 5
        strengths.append("OBJ file size is modest.")
    elif file_size_mb > 25:
        score -= 14
        warnings.append("OBJ file is large for a Roblox-ready export.")

    if bbox:
        dims = [max(value, 1e-6) for value in bbox]
        aspect_ratio = max(dims) / min(dims)
        flatness_ratio = min(dims) / max(dims)
        if archetype == "sword":
            if 4.0 <= aspect_ratio <= 28.0:
                score += 6
                strengths.append("Sword proportions are allowed to be long and thin.")
            elif aspect_ratio < 4.0:
                score -= 12
                warnings.append("Sword mesh is too squat; it may read like a knife, dagger, or chunky shard.")
            else:
                score -= 8
                warnings.append("Sword mesh is extremely thin; inspect edge depth before using it.")
        elif aspect_ratio <= 4.5:
            score += 8
            strengths.append("Bounding box proportions are stable.")
        elif aspect_ratio <= 8:
            score -= 7
            warnings.append("Bounding box is stretched; inspect the multi-angle render.")
        else:
            score -= 20
            warnings.append("Bounding box is extremely stretched or flat.")
        score += _prompt_shape_score(prompt, dims, warnings, strengths)
    else:
        score -= 16
        warnings.append("Bounding box could not be measured.")

    if object_count > 6:
        score -= 10
        warnings.append("Mesh appears split into many objects; Roblox import cleanup may be annoying.")
    elif 1 <= object_count <= 3:
        score += 3

    for warning in mesh_stats.get("warnings") or []:
        if warning:
            score -= 3
            warnings.append(str(warning))

    score = round(max(0.0, min(100.0, score)), 2)
    if score >= 82:
        status = "showcase_candidate"
    elif score >= 66:
        status = "needs_review"
    else:
        status = "reject"

    return GeometryQualityReport(
        score=score,
        status=status,
        warnings=_dedupe(warnings),
        strengths=_dedupe(strengths),
        metrics={
            "triangle_count": triangle_count,
            "file_size_mb": file_size_mb,
            "object_count": object_count,
            "aspect_ratio": round(aspect_ratio, 3) if aspect_ratio is not None else None,
            "flatness_ratio": round(flatness_ratio, 3) if flatness_ratio is not None else None,
            "archetype": archetype,
        },
    )


def _prompt_shape_score(prompt: str, dims: list[float], warnings: list[str], strengths: list[str]) -> float:
    archetype = _prompt_archetype(prompt)
    sorted_dims = sorted(dims)
    longest = sorted_dims[-1]
    shortest = sorted_dims[0]
    middle = sorted_dims[1]
    aspect = longest / shortest
    score = 0.0

    if archetype in {"crate", "chest", "box"}:
        if aspect <= 2.8:
            score += 8
            strengths.append("Prompt asks for a box-like prop and the mesh has box-like proportions.")
        else:
            score -= 12
            warnings.append("Prompt asks for a box-like prop but the mesh proportions are stretched.")
    elif archetype == "sword":
        width_to_length = middle / longest
        thickness_to_length = shortest / longest
        if aspect >= 3.0:
            score += 8
            strengths.append("Prompt asks for an elongated object and the mesh reads elongated.")
        else:
            score -= 12
            warnings.append("Prompt asks for an elongated object but the mesh is too chunky.")
        if 0.20 <= width_to_length <= 0.56 and thickness_to_length <= 0.12:
            score += 10
            strengths.append("Sword silhouette has a long blade profile with readable guard width.")
        elif width_to_length > 0.62:
            score -= 16
            warnings.append("Sword is too broad relative to its length; it may read like a dagger or short fantasy blade.")
        elif width_to_length < 0.12:
            score -= 8
            warnings.append("Sword is too narrow in silhouette; guard or blade shape may be hard to read.")
        if thickness_to_length > 0.18:
            score -= 8
            warnings.append("Sword appears too thick relative to length; inspect scale and side profile.")
    elif archetype == "sign":
        if aspect >= 3.0:
            score += 8
            strengths.append("Prompt asks for an elongated object and the mesh reads elongated.")
        else:
            score -= 12
            warnings.append("Prompt asks for an elongated object but the mesh is too chunky.")
    elif archetype in {"shield", "archway"}:
        if shortest / longest <= 0.35 and middle / longest >= 0.45:
            score += 8
            strengths.append("Prompt asks for a broad/flat object and the proportions support it.")
        else:
            score -= 8
            warnings.append("Prompt asks for a broad/flat object; proportions may not read correctly.")
    elif archetype in {"tower", "bottle", "tree", "stump"}:
        if aspect >= 1.6:
            score += 6
            strengths.append("Prompt asks for an upright prop and the mesh has enough height variation.")
        else:
            score -= 8
            warnings.append("Prompt asks for an upright prop but the mesh is too squat.")
    return score


def _prompt_archetype(prompt: str) -> str:
    text = prompt.lower()
    if any(word in text for word in ("crate", "barrel")):
        return "crate"
    if "chest" in text:
        return "chest"
    if "box" in text:
        return "box"
    if "sword" in text:
        return "sword"
    if "shield" in text:
        return "shield"
    if "sign" in text:
        return "sign"
    if "tower" in text:
        return "tower"
    if "bottle" in text or "potion" in text:
        return "bottle"
    if "tree" in text:
        return "tree"
    if "stump" in text:
        return "stump"
    if "arch" in text:
        return "archway"
    return "generic"


def _bbox(value: object) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    try:
        dims = [abs(float(item)) for item in value]
    except (TypeError, ValueError):
        return None
    if any(item <= 0 for item in dims):
        return None
    return dims


def _float(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
