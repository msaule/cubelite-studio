from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class BenchmarkRow:
    prompt: str
    profile: str
    success: bool
    generation_time_seconds: float
    peak_vram_gb: float | None
    output_file_size_mb: float | None
    triangle_count: int | None
    readiness_score: int | None
    error_message: str
    output_path: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_csv_row(self) -> dict[str, object]:
        return self.to_dict()
