from __future__ import annotations

import argparse
from pathlib import Path

from app.benchmark.benchmark_runner import run_benchmark
from app.config import ensure_project_dirs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CubeLite Studio benchmark prompts.")
    parser.add_argument("--dry-run", action="store_true", help="Use sample mesh instead of calling Cube 3D.")
    parser.add_argument("--profiles", nargs="*", default=["Low VRAM", "Balanced"], help="Profiles to benchmark.")
    parser.add_argument("--max-prompts", type=int, default=3, help="Maximum prompts to run.")
    parser.add_argument("--cube-repo-path", default="", help="Local Cube 3D repo path.")
    parser.add_argument("--model-weights-path", default="", help="Local Cube 3D model weights path.")
    parser.add_argument("--no-report", action="store_true", help="Skip technical report generation.")
    return parser.parse_args()


def main() -> None:
    ensure_project_dirs()
    args = parse_args()
    result = run_benchmark(
        profile_names=args.profiles,
        max_prompts=args.max_prompts,
        dry_run=args.dry_run,
        cube_repo_path=Path(args.cube_repo_path) if args.cube_repo_path else None,
        model_weights_path=Path(args.model_weights_path) if args.model_weights_path else None,
        create_report=not args.no_report,
    )
    print(f"CSV: {result.csv_path}")
    print(f"JSON: {result.json_path}")
    if result.report_path:
        print(f"Report: {result.report_path}")


if __name__ == "__main__":
    main()
