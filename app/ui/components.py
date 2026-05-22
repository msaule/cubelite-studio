from __future__ import annotations

from pathlib import Path


def list_recent_files(root: Path, patterns: tuple[str, ...], limit: int = 10) -> list[Path]:
    if not root.exists():
        return []
    files: list[Path] = []
    for pattern in patterns:
        files.extend(root.rglob(pattern))
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)[:limit]


def open_folder_hint(path: str | Path | None) -> str:
    return "No folder yet." if not path else f"Folder: {path}"
