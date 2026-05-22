from __future__ import annotations

import argparse
from pathlib import Path

from app.config import ensure_project_dirs, load_settings
from app.quality.candidate_search import CandidateSearchConfig, run_candidate_search


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a CubeLite multi-seed quality search.")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--profile", default="6GB Quality")
    parser.add_argument("--seeds", nargs="*", type=int, default=[11, 23, 37])
    parser.add_argument("--top-p", nargs="*", type=float, default=[0.9])
    parser.add_argument("--guidance", nargs="*", type=float, default=[1.0])
    parser.add_argument("--target-faces", type=int, default=16000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cube-repo-path", default="")
    parser.add_argument("--model-weights-path", default="")
    return parser.parse_args()


def main() -> None:
    ensure_project_dirs()
    settings = load_settings()
    args = parse_args()
    result = run_candidate_search(
        CandidateSearchConfig(
            prompt=args.prompt,
            profile_name=args.profile,
            seeds=tuple(args.seeds),
            top_p_values=tuple(args.top_p),
            guidance_scales=tuple(args.guidance),
            target_face_count=args.target_faces,
            dry_run=args.dry_run,
        ),
        cube_repo_path=Path(args.cube_repo_path or settings.cube_repo_path),
        model_weights_path=Path(args.model_weights_path or settings.model_weights_path),
    )
    print(f"Quality search: {result.json_path}")
    if result.best_candidate:
        print(f"Best score: {result.best_candidate.quality_score}")
        print(f"Best output: {result.best_candidate.output_path}")


if __name__ == "__main__":
    main()

