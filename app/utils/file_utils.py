from __future__ import annotations

import re
import shutil
from pathlib import Path

MAX_FOLDER_NAME = 64


def sanitize_prompt_for_path(prompt: str, fallback: str = "asset") -> str:
    cleaned = prompt.strip().lower()
    cleaned = cleaned.replace("\\", " ").replace("/", " ")
    cleaned = re.sub(r"\.\.+", " ", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    if not cleaned:
        cleaned = fallback
    reserved = {"con", "prn", "aux", "nul", "com1", "lpt1"}
    if cleaned in reserved:
        cleaned = f"{fallback}-{cleaned}"
    return cleaned[:MAX_FOLDER_NAME].strip("-") or fallback


def copy_if_exists(source: Path | None, destination: Path) -> Path | None:
    if source is None or not source.exists():
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def safe_display_path(path: Path | str | None, include_private: bool = False) -> str:
    if not path:
        return ""
    path_obj = Path(path)
    if include_private:
        return str(path_obj)
    parts = path_obj.parts
    if len(parts) <= 2:
        return path_obj.name
    return str(Path("...") / parts[-2] / parts[-1])
