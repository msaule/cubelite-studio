from __future__ import annotations

import argparse
from pathlib import Path

from app.benchmark.texture_benchmark import run_texture_benchmark
from app.config import ensure_project_dirs
from app.optimization.texture_generator import DEFAULT_DIFFUSERS_MODEL


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark CubeLite texture finishing providers.")
    parser.add_argument("--input-obj", default="sample_assets/sample_cube.obj")
    parser.add_argument("--prompt", default="low poly wooden crate game prop")
    parser.add_argument("--providers", nargs="*", default=["studio"])
    parser.add_argument("--model-id", default=DEFAULT_DIFFUSERS_MODEL)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    ensure_project_dirs()
    args = parse_args()
    result = run_texture_benchmark(
        input_obj=Path(args.input_obj),
        prompt=args.prompt,
        providers=args.providers,
        model_id=args.model_id,
        texture_size=args.size,
        steps=args.steps,
        seed=args.seed,
    )
    print(f"Texture benchmark: {result}")


if __name__ == "__main__":
    main()
