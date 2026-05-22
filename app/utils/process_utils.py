from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class ProcessResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    elapsed_seconds: float

    @property
    def combined_logs(self) -> str:
        return "\n".join(part for part in (self.stdout, self.stderr) if part)


def run_command(command: Iterable[str], cwd: Path | None = None, timeout: int | None = None) -> ProcessResult:
    command_list = [str(part) for part in command]
    started = time.perf_counter()
    completed = subprocess.run(
        command_list,
        cwd=str(cwd) if cwd else None,
        shell=False,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return ProcessResult(
        command=command_list,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        elapsed_seconds=time.perf_counter() - started,
    )
