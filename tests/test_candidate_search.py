from pathlib import Path

from app.quality.candidate_search import CandidateSearchConfig, run_candidate_search, score_candidate


def test_score_candidate_caps_rejected_geometry() -> None:
    score = score_candidate(
        {"success": True, "readiness_score": 100, "prompt": "simple wooden crate"},
        {
            "mesh_stats": {
                "success": True,
                "triangle_count": 80,
                "file_size_mb": 0.01,
                "object_count": 1,
                "bounding_box_dimensions": (10.0, 0.1, 0.1),
                "warnings": [],
            }
        },
    )

    assert score < 75


def test_candidate_search_dry_run_writes_json_and_markdown(tmp_path: Path) -> None:
    result = run_candidate_search(
        CandidateSearchConfig(
            prompt="low poly wooden crate game prop",
            profile_name="Benchmark Safe",
            seeds=(1,),
            dry_run=True,
        ),
        cube_repo_path="",
        model_weights_path="",
        outputs_dir=tmp_path / "outputs",
        reports_dir=tmp_path / "reports",
    )

    assert Path(result.json_path).exists()
    assert Path(result.json_path).with_suffix(".md").exists()
    assert result.best_candidate is not None
    assert result.best_candidate.geometry_status in {"showcase_candidate", "needs_review", "reject"}
