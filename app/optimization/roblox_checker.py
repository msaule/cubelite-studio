from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.optimization.mesh_analyzer import MeshStats


@dataclass
class RobloxReadinessReport:
    score: int
    status: str
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    prompt_improvement_tips: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_text(self) -> str:
        lines = [
            "CubeLite Studio Roblox Import Notes",
            "",
            "This is a heuristic readiness check, not an official Roblox validation.",
            f"Score: {self.score}/100",
            f"Status: {self.status}",
            "",
            self.summary,
            "",
            "Warnings:",
            *(f"- {warning}" for warning in self.warnings or ["None"]),
            "",
            "Recommended actions:",
            *(f"- {action}" for action in self.recommended_actions or ["Ready to test in Roblox Studio."]),
            "",
            "Prompt improvement tips:",
            *(f"- {tip}" for tip in self.prompt_improvement_tips or ["Keep prompts focused on one simple object."]),
        ]
        return "\n".join(lines) + "\n"


def check_roblox_readiness(stats: MeshStats, simplification_failed: bool = False) -> RobloxReadinessReport:
    score = 100
    warnings: list[str] = []
    actions: list[str] = []
    tips = [
        "Try adding 'low poly'.",
        "Generate a single object, not a full scene.",
        "Avoid 'ultra detailed' for low-VRAM workflows.",
        "Check scale inside Roblox Studio after import.",
    ]

    if not stats.success:
        return RobloxReadinessReport(
            score=0,
            status="Failed",
            summary="Mesh analysis failed, so the asset is not ready to test.",
            warnings=[stats.error_message or "Mesh failed to load."],
            recommended_actions=["Regenerate the mesh or inspect the OBJ file manually."],
            prompt_improvement_tips=tips,
        )

    if stats.triangle_count <= 0 or stats.vertex_count <= 0:
        score -= 80
        warnings.append("Mesh appears to be missing usable geometry.")
        actions.append("Regenerate the asset with a simpler prompt.")
    if stats.triangle_count > 50000:
        score -= 35
        warnings.append(f"Triangle count is high ({stats.triangle_count}).")
        actions.append("Simplify before importing into Roblox Studio.")
    elif stats.triangle_count > 20000:
        score -= 18
        warnings.append(f"Triangle count is moderately high ({stats.triangle_count}).")
        actions.append("Consider simplification for better runtime performance.")
    if stats.file_size_mb > 25:
        score -= 20
        warnings.append(f"OBJ file is large ({stats.file_size_mb} MB).")
        actions.append("Simplify the mesh or regenerate with simpler geometry.")
    if stats.approximate_scale is not None and (stats.approximate_scale > 100 or stats.approximate_scale < 0.01):
        score -= 12
        warnings.append(f"Mesh scale looks unusual (approximate scale {stats.approximate_scale}).")
        actions.append("Verify scale after importing into Roblox Studio.")
    if stats.object_count and stats.object_count > 8:
        score -= 10
        warnings.append(f"Mesh contains many detected objects/groups ({stats.object_count}).")
        actions.append("Prefer a single-object prompt for Roblox asset workflows.")
    if simplification_failed:
        score -= 8
        warnings.append("Simplification was requested but did not complete.")
        actions.append("Install pymeshlab or simplify in a dedicated 3D tool.")

    score = max(0, min(100, score))
    if score >= 80:
        status = "Ready to test"
    elif score >= 55:
        status = "Needs simplification"
    elif score > 0:
        status = "Too heavy"
    else:
        status = "Failed"

    summary = "The mesh looks reasonable for a first Roblox Studio import test." if score >= 80 else "The mesh may need cleanup before Roblox Studio import testing."
    return RobloxReadinessReport(
        score=score,
        status=status,
        summary=summary,
        warnings=warnings,
        recommended_actions=actions,
        prompt_improvement_tips=tips,
    )
