from app.cube.asset_styles import get_style, strengthen_prompt, style_names


def test_style_names_include_core_styles() -> None:
    assert "Roblox Low Poly" in style_names()
    assert "Sci-Fi Plastic" in style_names()


def test_strengthen_prompt_adds_style_terms() -> None:
    prompt = strengthen_prompt("wooden crate", "Roblox Low Poly")

    assert "wooden crate" in prompt
    assert "single object" in prompt
    assert "avoid:" in prompt


def test_unknown_style_falls_back_to_low_poly() -> None:
    assert get_style("unknown").name == "Roblox Low Poly"
