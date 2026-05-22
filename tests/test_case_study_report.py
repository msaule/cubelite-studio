import json
from pathlib import Path

from app.reporting.case_study import discover_case_study_assets, generate_case_study_pack, summarize_case_study_assets


def test_case_study_discovers_assets_and_summarizes(tmp_path: Path) -> None:
    asset_dir = tmp_path / "asset-one"
    asset_dir.mkdir()
    (asset_dir / "original.obj").write_text("o x\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n", encoding="utf-8")
    (asset_dir / "metadata.json").write_text(
        json.dumps(
            {
                "prompt": "low poly test crate",
                "profile": "Low VRAM",
                "readiness_score": 92,
                "readiness_status": "Ready to test",
                "peak_vram_gb": 3.932,
                "generation_time_seconds": 210.0,
                "original_mesh_stats": {"triangle_count": 128},
            }
        ),
        encoding="utf-8",
    )

    assets = discover_case_study_assets(tmp_path)
    summary = summarize_case_study_assets(assets)

    assert len(assets) == 1
    assert assets[0].prompt == "low poly test crate"
    assert summary.asset_count == 1
    assert summary.max_peak_vram_gb == 3.932
    assert summary.average_readiness_score == 92


def test_case_study_pack_writes_markdown_and_html(tmp_path: Path) -> None:
    examples = tmp_path / "examples"
    asset_dir = examples / "asset-two"
    asset_dir.mkdir(parents=True)
    (asset_dir / "metadata.json").write_text(
        json.dumps(
            {
                "prompt": "simple wooden crate",
                "profile": "Low VRAM",
                "readiness_score": 90,
                "readiness_status": "Ready to test",
                "peak_vram_gb": 4.0,
                "generation_time_seconds": 200.0,
                "original_mesh_stats": {"triangle_count": 1000},
            }
        ),
        encoding="utf-8",
    )

    markdown_path, _contact_sheet, html_path = generate_case_study_pack(tmp_path / "reports", examples)

    assert markdown_path.exists()
    assert html_path.exists()
    assert "Consumer-GPU Case Study" in markdown_path.read_text(encoding="utf-8")
    assert "simple wooden crate" in html_path.read_text(encoding="utf-8")
