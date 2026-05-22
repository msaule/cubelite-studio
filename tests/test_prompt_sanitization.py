from app.utils.file_utils import sanitize_prompt_for_path


def test_prompt_sanitization_blocks_path_traversal() -> None:
    value = sanitize_prompt_for_path("../../weird: prompt? * with / slashes")
    assert ".." not in value
    assert "/" not in value
    assert "\\" not in value
    assert value


def test_prompt_sanitization_handles_empty_and_reserved_names() -> None:
    assert sanitize_prompt_for_path("   ") == "asset"
    assert sanitize_prompt_for_path("CON") == "asset-con"
