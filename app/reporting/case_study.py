from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from html import escape
from pathlib import Path
from statistics import mean

from app.config import REPORTS_DIR, SAMPLE_ASSETS_DIR, version_string
from app.utils.time_utils import utc_timestamp

REAL_EXAMPLES_DIR = SAMPLE_ASSETS_DIR / "real_cube_examples"


@dataclass
class CaseStudyAsset:
    name: str
    prompt: str
    profile: str
    preview_path: str | None
    original_obj_path: str | None
    readiness_score: int | None
    triangle_count: int | None
    peak_vram_gb: float | None
    generation_time_seconds: float | None
    status: str
    quality_label: str = "Unreviewed"
    reviewer_note: str = ""
    showcase_rank: int | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class CaseStudySummary:
    asset_count: int
    successful_asset_count: int
    average_generation_seconds: float | None
    max_peak_vram_gb: float | None
    average_triangles: float | None
    average_readiness_score: float | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def discover_case_study_assets(examples_dir: Path = REAL_EXAMPLES_DIR) -> list[CaseStudyAsset]:
    if not examples_dir.exists():
        return []

    curation = _load_curation(examples_dir)
    assets: list[CaseStudyAsset] = []
    for metadata_path in sorted(examples_dir.glob("*/metadata.json")):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        original_stats = metadata.get("original_mesh_stats") or {}
        final_stats = metadata.get("optimized_mesh_stats") or original_stats
        preview = metadata_path.parent / "preview.png"
        original = metadata_path.parent / "original.obj"
        curated = curation.get(metadata_path.parent.name, {})
        assets.append(
            CaseStudyAsset(
                name=metadata_path.parent.name,
                prompt=str(metadata.get("prompt", "")),
                profile=str(metadata.get("profile", "")),
                preview_path=str(preview) if preview.exists() else None,
                original_obj_path=str(original) if original.exists() else None,
                readiness_score=_optional_int(metadata.get("readiness_score")),
                triangle_count=_optional_int(final_stats.get("triangle_count")),
                peak_vram_gb=_optional_float(metadata.get("peak_vram_gb")),
                generation_time_seconds=_optional_float(metadata.get("generation_time_seconds")),
                status=str(metadata.get("readiness_status", "n/a")),
                quality_label=str(curated.get("quality_label", "Unreviewed")),
                reviewer_note=str(curated.get("reviewer_note", "")),
                showcase_rank=_optional_int(curated.get("showcase_rank")),
            )
        )
    return sorted(assets, key=lambda asset: (asset.showcase_rank is None, asset.showcase_rank or 9999, asset.name))


def summarize_case_study_assets(assets: list[CaseStudyAsset]) -> CaseStudySummary:
    successes = [asset for asset in assets if asset.readiness_score is not None and asset.triangle_count is not None]
    return CaseStudySummary(
        asset_count=len(assets),
        successful_asset_count=len(successes),
        average_generation_seconds=_mean_or_none(asset.generation_time_seconds for asset in successes),
        max_peak_vram_gb=max((asset.peak_vram_gb for asset in successes if asset.peak_vram_gb is not None), default=None),
        average_triangles=_mean_or_none(asset.triangle_count for asset in successes),
        average_readiness_score=_mean_or_none(asset.readiness_score for asset in successes),
    )


def generate_contact_sheet(
    assets: list[CaseStudyAsset],
    output_path: Path,
    max_assets: int = 6,
) -> Path | None:
    previews = [asset for asset in assets if asset.preview_path][:max_assets]
    if not previews:
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.image as mpimg
        import matplotlib.pyplot as plt
    except Exception:
        return None

    columns = min(3, len(previews))
    rows = (len(previews) + columns - 1) // columns
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(rows, columns, figsize=(columns * 4, rows * 4), dpi=140)
    if not isinstance(axes, (list, tuple)):
        axes_list = list(getattr(axes, "flat", [axes]))
    else:
        axes_list = list(axes)
    for axis in axes_list:
        axis.axis("off")
    for axis, asset in zip(axes_list, previews):
        image = mpimg.imread(asset.preview_path)
        axis.imshow(image)
        title = asset.prompt[:58] + ("..." if len(asset.prompt) > 58 else "")
        axis.set_title(title, fontsize=8)
        axis.axis("off")
    fig.patch.set_facecolor("#f7f8fa")
    plt.tight_layout(pad=1.0)
    fig.savefig(output_path, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    return output_path


def generate_case_study_pack(
    reports_dir: Path = REPORTS_DIR,
    examples_dir: Path = REAL_EXAMPLES_DIR,
) -> tuple[Path, Path | None, Path]:
    assets = discover_case_study_assets(examples_dir)
    summary = summarize_case_study_assets(assets)
    stamp = utc_timestamp()
    reports_dir.mkdir(parents=True, exist_ok=True)
    contact_sheet = generate_contact_sheet(assets, reports_dir / f"cubelite-real-results-contact-sheet-{stamp}.png")
    markdown_path = reports_dir / f"cubelite-roblox-case-study-{stamp}.md"
    html_path = reports_dir / f"cubelite-roblox-case-study-{stamp}.html"
    markdown_path.write_text(_case_study_markdown(summary, assets, contact_sheet), encoding="utf-8")
    html_path.write_text(_case_study_html(summary, assets, contact_sheet, html_path.parent), encoding="utf-8")
    return markdown_path, contact_sheet, html_path


def _case_study_markdown(
    summary: CaseStudySummary,
    assets: list[CaseStudyAsset],
    contact_sheet: Path | None,
) -> str:
    image_line = f"![Real CubeLite outputs]({contact_sheet.name})\n\n" if contact_sheet else ""
    rows = "\n".join(
        "| "
        + " | ".join(
            [
                asset.prompt.replace("|", "/"),
                asset.profile,
                "" if asset.generation_time_seconds is None else f"{asset.generation_time_seconds:.1f}",
                "" if asset.peak_vram_gb is None else f"{asset.peak_vram_gb:.2f}",
                "" if asset.triangle_count is None else str(asset.triangle_count),
                "" if asset.readiness_score is None else str(asset.readiness_score),
                asset.quality_label.replace("|", "/"),
                asset.status,
            ]
        )
        + " |"
        for asset in assets
    )
    return f"""# CubeLite Studio: Roblox Cube 3D Consumer-GPU Case Study

{image_line}## Executive Summary

CubeLite Studio is an independent local toolkit around Roblox Cube 3D. The project does not claim ownership of Cube 3D, does not redistribute model weights, and is not affiliated with Roblox Corporation.

The technical result is practical: on an RTX 4050 Laptop GPU with 6GB VRAM, the official high-memory path failed with CUDA out-of-memory near 5.98GB peak VRAM, while CubeLite's staged low-VRAM runner completed real Cube 3D v0.5 generations at about {summary.max_peak_vram_gb or 0:.2f}GB peak observed VRAM.

## Why This Is Interesting

- It turns Cube 3D experimentation into a measurable local workflow for everyday Roblox creators.
- It records actual VRAM, time, triangle count, readiness, and failure reasons.
- It exports Roblox-oriented asset folders instead of leaving users with raw model output.
- It presents honest limitations and mixed outputs instead of pretending every generation is production-ready.

## Real Local Evidence

- Real generated assets discovered: {summary.asset_count}
- Assets with mesh/readiness data: {summary.successful_asset_count}
- Average generation time: {_fmt(summary.average_generation_seconds, ' seconds')}
- Peak observed low-VRAM run: {_fmt(summary.max_peak_vram_gb, ' GB')}
- Average triangle count: {_fmt(summary.average_triangles, '')}
- Average readiness score: {_fmt(summary.average_readiness_score, '/100')}

Readiness is a Roblox-import heuristic, not a semantic quality score. The quality column separates showcase outputs from mixed or failed shapes.

| Prompt | Profile | Seconds | Peak VRAM GB | Triangles | Readiness | Quality | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
{rows}

## Low-VRAM Engineering Approach

CubeLite's experimental runner reduces peak memory by staging the pipeline:

- CLIP text encoding stays on CPU.
- The GPT token generator is loaded on GPU only for token generation.
- Classifier-free guidance is disabled in the lowest-VRAM profile.
- GPT KV cache is avoided for the lowest-VRAM profile.
- GPT and CLIP are unloaded before the shape decoder is loaded.
- Shape decoding uses `bfloat16` and a smaller chunk size.

## Product Layer

CubeLite Studio adds a creator-facing Streamlit app with Generate, Benchmark, Results, System Check, Settings, Case Study, and About tabs. It includes dry-run mode, official-path configuration, a command-template writer, local previews, export packages, benchmark CSV/JSON, and technical report generation.

## Honest Limitations

- This is not official Roblox validation.
- Generated meshes are geometry-first; material and texture workflows still need inspection.
- Prompt quality matters, and some outputs are mixed.
- Real Cube 3D weights must come from official sources.
- Benchmarks so far are from one consumer laptop GPU and should be expanded across more hardware.

## Practical Value

CubeLite Studio is an independent low-VRAM workflow and benchmarking layer around Roblox Cube 3D. On this 6GB RTX 4050 Laptop GPU, the official high-memory path hit CUDA OOM, while a staged CubeLite runner completed real Cube 3D v0.5 generations at about {summary.max_peak_vram_gb or 0:.2f}GB peak VRAM. The project includes a local creator app, benchmark runner, mesh/readiness analysis, UV/texturing finishing, export packaging, and technical report generation for Roblox creator workflows.

CubeLite Studio version: {version_string()}
"""


def _case_study_html(
    summary: CaseStudySummary,
    assets: list[CaseStudyAsset],
    contact_sheet: Path | None,
    base_dir: Path,
) -> str:
    cards = "\n".join(_asset_card(asset, base_dir) for asset in assets)
    contact = f'<img class="contact" src="{escape(_relative_asset_path(contact_sheet, base_dir))}" alt="CubeLite real output contact sheet">' if contact_sheet else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>CubeLite Studio Case Study</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; color: #172033; background: #f6f7f9; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 40px 24px; }}
    h1 {{ font-size: 38px; margin-bottom: 8px; }}
    h2 {{ margin-top: 34px; }}
    .lead {{ font-size: 18px; line-height: 1.5; max-width: 860px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 24px 0; }}
    .metric, .card {{ background: white; border: 1px solid #dde1e7; border-radius: 8px; padding: 16px; }}
    .metric strong {{ display: block; font-size: 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }}
    .card img {{ width: 100%; border-radius: 6px; border: 1px solid #e1e5eb; background: #f7f8fa; }}
    .contact {{ width: 100%; border-radius: 8px; border: 1px solid #dde1e7; background: white; }}
    .muted {{ color: #596579; }}
    code {{ background: #eceff3; padding: 2px 5px; border-radius: 4px; }}
  </style>
</head>
<body>
<main>
  <p class="muted">Independent technical case study. Not affiliated with Roblox Corporation.</p>
  <h1>CubeLite Studio</h1>
  <p class="lead">Low-VRAM Cube 3D workflow and benchmarking toolkit for Roblox creators. Real Cube 3D v0.5 generations completed on a 6GB RTX 4050 Laptop GPU after the official high-memory path hit CUDA out-of-memory.</p>
  <section class="metrics">
    <div class="metric"><span>Real assets</span><strong>{summary.asset_count}</strong></div>
    <div class="metric"><span>Peak VRAM</span><strong>{_fmt(summary.max_peak_vram_gb, ' GB')}</strong></div>
    <div class="metric"><span>Avg seconds</span><strong>{_fmt(summary.average_generation_seconds, '')}</strong></div>
    <div class="metric"><span>Avg readiness</span><strong>{_fmt(summary.average_readiness_score, '/100')}</strong></div>
  </section>
  {contact}
  <h2>Generated Evidence</h2>
  <section class="grid">{cards}</section>
  <h2>Low-VRAM Method</h2>
  <p>CubeLite stages CLIP, GPT, and shape decoding separately; keeps CLIP on CPU; disables guidance for the lowest profile; avoids KV cache; unloads GPT before decoding; and decodes with <code>bfloat16</code> plus smaller chunks.</p>
  <h2>Honest Limitations</h2>
  <p>This is not official Roblox validation. The outputs are geometry-first, prompt-sensitive, and should be tested inside Roblox Studio. CubeLite does not redistribute Cube 3D weights.</p>
</main>
</body>
</html>
"""


def _asset_card(asset: CaseStudyAsset, base_dir: Path) -> str:
    image = f'<img src="{escape(_relative_asset_path(Path(asset.preview_path), base_dir))}" alt="{escape(asset.prompt)}">' if asset.preview_path else ""
    return f"""<article class="card">
  {image}
  <h3>{escape(asset.prompt[:72])}</h3>
  <p class="muted">{escape(asset.profile)} · {escape(asset.status)}</p>
  <p>{escape(asset.quality_label)} · {_fmt(asset.generation_time_seconds, ' sec')} · {_fmt(asset.peak_vram_gb, ' GB VRAM')} · {_fmt(asset.triangle_count, ' tris')} · {_fmt(asset.readiness_score, '/100')}</p>
  <p class="muted">{escape(asset.reviewer_note)}</p>
</article>"""


def _load_curation(examples_dir: Path) -> dict[str, dict[str, object]]:
    curation_path = examples_dir / "curation.json"
    if not curation_path.exists():
        return {}
    try:
        data = json.loads(curation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _relative_asset_path(path: Path, base_dir: Path) -> str:
    try:
        return Path(os.path.relpath(path.resolve(), base_dir.resolve())).as_posix()
    except OSError:
        return path.as_posix()


def _fmt(value: float | int | None, suffix: str) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}{suffix}"
    return f"{value}{suffix}"


def _mean_or_none(values) -> float | None:
    cleaned = [float(value) for value in values if value is not None]
    return mean(cleaned) if cleaned else None


def _optional_float(value) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value) -> int | None:
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError):
        return None
