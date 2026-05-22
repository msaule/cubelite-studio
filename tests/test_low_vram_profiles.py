from app.cube.low_vram_profiles import recommend_profile


def test_profile_selection_by_vram() -> None:
    assert recommend_profile(6).name == "Low VRAM"
    assert recommend_profile(8).name in {"Low VRAM", "Balanced"}
    assert recommend_profile(12).name == "Balanced"
    assert recommend_profile(16).name == "High Quality"
    assert recommend_profile(24).name == "High Quality"
