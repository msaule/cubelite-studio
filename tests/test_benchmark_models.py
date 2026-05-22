import csv
import json
from pathlib import Path

from app.benchmark.benchmark_models import BenchmarkRow


def test_benchmark_row_serializes_to_csv_and_json(tmp_path: Path) -> None:
    row = BenchmarkRow(
        prompt="simple wooden crate",
        profile="Low VRAM",
        success=False,
        generation_time_seconds=1.25,
        peak_vram_gb=None,
        output_file_size_mb=None,
        triangle_count=None,
        readiness_score=None,
        error_message="missing weights",
        output_path=None,
    )
    csv_path = tmp_path / "rows.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row.to_csv_row().keys()))
        writer.writeheader()
        writer.writerow(row.to_csv_row())
    json_path = tmp_path / "rows.json"
    json_path.write_text(json.dumps([row.to_dict()]), encoding="utf-8")

    assert "missing weights" in csv_path.read_text(encoding="utf-8")
    assert json.loads(json_path.read_text(encoding="utf-8"))[0]["success"] is False
