from app.quality.geometry_quality import assess_geometry_quality


def test_geometry_quality_accepts_box_like_crate() -> None:
    report = assess_geometry_quality(
        "low poly wooden crate game prop",
        {
            "success": True,
            "triangle_count": 3200,
            "file_size_mb": 1.2,
            "object_count": 1,
            "bounding_box_dimensions": (1.0, 1.1, 0.9),
            "warnings": [],
        },
    )

    assert report.status == "showcase_candidate"
    assert report.score >= 82
    assert report.metrics["archetype"] == "crate"


def test_geometry_quality_rejects_stretched_crate() -> None:
    report = assess_geometry_quality(
        "simple wooden crate",
        {
            "success": True,
            "triangle_count": 160,
            "file_size_mb": 0.1,
            "object_count": 1,
            "bounding_box_dimensions": (12.0, 0.2, 0.2),
            "warnings": [],
        },
    )

    assert report.status == "reject"
    assert any("stretched" in warning for warning in report.warnings)


def test_geometry_quality_rejects_failed_mesh() -> None:
    report = assess_geometry_quality("anything", {"success": False})

    assert report.score == 0
    assert report.status == "reject"
