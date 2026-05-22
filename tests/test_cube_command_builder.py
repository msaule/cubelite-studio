import json
import sys
from pathlib import Path

import pytest

from app.cube.cube_command_builder import build_cubelite_low_vram_template, write_cubelite_low_vram_template


def test_low_vram_template_uses_safe_argument_list(tmp_path: Path) -> None:
    command = build_cubelite_low_vram_template(tmp_path, python_executable=sys.executable)

    assert command[0] == sys.executable
    assert "cubelite_low_vram_generate.py" in command[1]
    assert "{prompt}" in command
    assert "{output_dir}" in command
    assert "--guidance-scale" in command
    assert "--chunk-size" in command


def test_write_low_vram_template_respects_overwrite(tmp_path: Path) -> None:
    template_path = write_cubelite_low_vram_template(tmp_path, python_executable=sys.executable)
    data = json.loads(template_path.read_text(encoding="utf-8"))

    assert template_path.name == "cubelite_cube_command.json"
    assert data["command"][0] == sys.executable
    with pytest.raises(FileExistsError):
        write_cubelite_low_vram_template(tmp_path, python_executable=sys.executable)

    write_cubelite_low_vram_template(tmp_path, python_executable=sys.executable, overwrite=True)
