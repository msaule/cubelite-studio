# CubeLite Studio: Low-VRAM Cube 3D Workflow Benchmark

## 1. Summary

CubeLite Studio is an independent local toolkit for testing Roblox Cube 3D workflows on consumer hardware. This report summarizes an experimental low-VRAM workflow, early benchmark results, mesh complexity, and heuristic Roblox-readiness checks. It is not official validation.

- Runs completed: 3
- Successful runs: 3
- Failed runs: 0
- Average generation time: 218.25 seconds
- Peak observed VRAM: 3.93 GB

## 2. Test Machine Specs

- OS: Windows 11
- CPU: Intel64 Family 6 Model 186 Stepping 2, GenuineIntel
- RAM: 15.75 GB
- Python: 3.13.9
- PyTorch: 2.11.0+cpu
- CUDA available: False
- CUDA version: None
- GPU: NVIDIA GeForce RTX 4050 Laptop GPU
- Total VRAM: 6.0 GB
- Free VRAM at check: 5.78 GB
- Recommended profile: Low VRAM

## 3. Cube 3D Setup

Cube 3D setup path is user-configured and weights are not redistributed by CubeLite Studio.

CubeLite Studio does not include or redistribute Cube 3D model weights. Users must obtain model files from official sources and follow the original license.

## 4. Profiles Tested

- Benchmark Safe: target Minimum practical GB, resolution base 4.0, fp16=True, cpu_offload=True, fast_inference=False

## 5. Benchmark Prompt Set

- low poly fantasy sword, single object
- simple wooden crate, game asset
- stylized potion bottle, single object

## 6. Results Table

| Prompt | Profile | Success | Seconds | Peak VRAM GB | Triangles | Readiness | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| low poly fantasy sword, single object | Benchmark Safe | yes | 217.08 | 3.93 | 156 | 92 |  |
| simple wooden crate, game asset | Benchmark Safe | yes | 218.43 | 3.93 | 2856 | 92 |  |
| stylized potion bottle, single object | Benchmark Safe | yes | 219.25 | 3.93 | 968 | 92 |  |

## 7. VRAM Usage Comparison

Peak VRAM is recorded when NVIDIA telemetry is available through PyNVML or PyTorch CUDA memory APIs. Missing values mean VRAM telemetry was unavailable, not that no VRAM was used.

## 8. Generation Time Comparison

Generation time includes CubeLite orchestration and Cube process runtime. Dry-run rows are useful for validating the pipeline, but they are not model inference measurements.

## 9. Mesh Complexity Comparison

Triangle count and file size are measured from generated OBJ files where mesh loading succeeds. These values are practical indicators for Roblox import testing, not artistic quality scores.

## 10. Roblox Readiness Results

Readiness scores are heuristic and intentionally conservative. They flag high triangle counts, large files, unusual scale, missing geometry, and simplification failures.

## 11. What Worked

- Local dry-run workflow validates the complete pipeline without model files.
- Benchmark rows are preserved even when individual generations fail.
- Export packages include original mesh, optional optimized mesh, metadata, and Roblox import notes.

## 12. What Failed

Failures are captured in the results table. Typical failure classes include missing Cube 3D paths, missing weights, CUDA out-of-memory errors, subprocess failures, or missing OBJ outputs.

## 13. Limitations

- This project is independent and not affiliated with Roblox Corporation.
- Low-VRAM settings are workflow preferences unless the detected Cube command template maps them to supported Cube 3D options.
- Mesh readiness is a heuristic helper, not an official Roblox validation.
- Dry-run mode does not measure Cube 3D quality, speed, or VRAM usage.

## 14. Next Steps

- Add validated command templates for specific Cube 3D releases.
- Expand benchmark coverage across 6GB, 8GB, 12GB, 16GB, and 24GB GPUs.
- Add optional visual previews and turntable renders.
- Compare simplification quality across pymeshlab and other mesh tools.

## Potential Value for Roblox Creators

- Lowers the barrier for local experimentation.
- Gives creators clearer hardware expectations.
- Turns raw mesh generation into a Roblox import workflow.
- Helps identify where generation fails on consumer hardware.
- Creates benchmark data instead of vague guesses.
