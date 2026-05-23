from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from app.config import BENCHMARKS_DIR
from app.optimization.asset_finisher import finish_asset_for_roblox
from app.optimization.texture_analyzer import analyze_texture
from app.utils.time_utils import utc_timestamp


@dataclass
class TextureBenchmarkRow:
    prompt: str
    provider: str
    model_id: str | None
    success: bool
    elapsed_seconds: float
    texture_path: str | None
    textured_obj_path: str | None
    texture_width: int | None
    texture_height: int | None
    texture_file_size_mb: float | None
    texture_contrast_score: float | None
    texture_color_variance_score: float | None
    error_message: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def run_texture_benchmark(
    input_obj: Path,
    prompt: str,
    providers: list[str],
    output_dir: Path = BENCHMARKS_DIR,
    model_id: str | None = None,
    texture_size: int = 512,
    steps: int = 4,
    seed: int = 0,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[TextureBenchmarkRow] = []
    stamp = utc_timestamp()
    for provider in providers:
        run_dir = output_dir / f"texture-{provider}-{stamp}"
        started = time.perf_counter()
        result = finish_asset_for_roblox(
            input_obj=input_obj,
            output_dir=run_dir,
            prompt=prompt,
            texture_provider=provider,
            texture_model_id=model_id,
            texture_steps=steps,
            texture_size=texture_size,
            texture_seed=seed,
        )
        texture_stats = analyze_texture(Path(result.texture_path)) if result.texture_path else None
        rows.append(
            TextureBenchmarkRow(
                prompt=prompt,
                provider=provider,
                model_id=model_id if provider in {"diffusers", "neural"} else None,
                success=result.success,
                elapsed_seconds=round(time.perf_counter() - started, 3),
                texture_path=result.texture_path,
                textured_obj_path=result.textured_obj_path,
                texture_width=texture_stats.width if texture_stats else None,
                texture_height=texture_stats.height if texture_stats else None,
                texture_file_size_mb=texture_stats.file_size_mb if texture_stats else None,
                texture_contrast_score=texture_stats.contrast_score if texture_stats else None,
                texture_color_variance_score=texture_stats.color_variance_score if texture_stats else None,
                error_message=result.error_message,
            )
        )

    json_path = output_dir / f"texture-benchmark-{stamp}.json"
    json_path.write_text(json.dumps([row.to_dict() for row in rows], indent=2), encoding="utf-8")
    return json_path
