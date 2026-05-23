# CubeLite Studio

> Low-VRAM Cube 3D workflow and benchmarking toolkit for Roblox creators.

![CubeLite Studio local app](sample_assets/cubelite-studio-ui.png)

CubeLite Studio is an independent local toolkit that helps Roblox creators test Roblox Cube 3D on consumer GPUs, measure VRAM usage, analyze generated OBJ meshes, and export Roblox-friendly asset packages. It does not include Cube 3D model weights and is not affiliated with, sponsored by, or endorsed by Roblox Corporation.

## Why This Project Exists

Roblox Cube 3D is an open-source 3D generation model designed for text-to-shape workflows and game-engine asset generation. The official setup is aimed at higher-end GPU environments, while many everyday Roblox developers work on laptops or desktops with 6GB, 8GB, or 12GB of VRAM. CubeLite Studio explores a practical creator workflow around that gap: low-VRAM profiles, repeatable benchmarks, mesh inspection, optional simplification, and Roblox-ready export folders.

The goal is not to claim ownership of Cube 3D, retrain a foundation model, or present a fake compatibility layer. The goal is a technically honest case study: test Cube 3D on consumer hardware, identify practical bottlenecks, and make the output easier to measure and prepare for Roblox Studio.

## Key Features

- Streamlit local app for generation, benchmarks, system checks, settings, and results.
- Dry-run mode that works without Cube 3D installed.
- Low-VRAM, Balanced, High Quality, Benchmark Safe, and Auto profiles.
- GPU, CUDA, PyTorch, RAM, and dependency diagnostics.
- VRAM monitoring through PyNVML or PyTorch when available.
- OBJ mesh analysis with vertex count, triangle count, file size, scale, normals, materials, and warnings.
- Local PNG preview rendering for generated OBJ meshes.
- Multi-angle mesh inspection plates.
- Heuristic Roblox-readiness report.
- Optional mesh simplification through `pymeshlab`.
- UV unwrapping through `xatlas` plus OBJ/MTL material-map output.
- Studio material provider that generates clean albedo, normal, roughness, and metallic maps.
- Optional Diffusers texture provider for local neural atlas experiments, kept behind an experimental path.
- Export packages containing OBJ files, textured OBJ files, metadata, import notes, and benchmark summaries.
- Benchmark CSV, JSON, and technical Markdown report generation.
- Candidate curation that runs multiple seeds/settings, renders inspection plates, scores geometry, and rejects weak meshes before packaging.
- Style presets that strengthen prompts and change material output for low-poly, toybox, sci-fi, fantasy, medieval, and crystal props.
- Roblox-reviewable case study pack with real-output contact sheet, HTML summary, and technical framing.

## Quick Start

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Launch the app:

```bash
python run_app.py
```

Run a dry-run benchmark:

```bash
python run_benchmark.py --dry-run
```

Run a candidate curation pass:

```bash
python run_quality_search.py --prompt "low poly wooden crate game prop, clean silhouette" --profile "6GB Quality" --style "Roblox Low Poly" --seeds 101 202 303
```

Run a texture-provider benchmark:

```bash
python run_texture_benchmark.py --providers procedural
python run_texture_benchmark.py --providers studio --size 1024
python run_texture_benchmark.py --providers diffusers --size 128 --steps 2
python run_texture_benchmark.py --providers diffusers --model-id stable-diffusion-v1-5/stable-diffusion-v1-5 --size 512 --steps 24
```

## Dry Run Mode

Dry run mode uses a small valid sample OBJ mesh and does not call Cube 3D. This lets reviewers and contributors test the complete CubeLite pipeline immediately:

- prompt entry
- profile selection
- mesh analysis
- UV unwrap and material-map finishing
- Roblox-readiness scoring
- export package creation
- benchmark CSV/JSON generation
- technical report generation

Dry-run results are useful for validating workflow behavior. They are not Cube 3D quality, speed, or VRAM measurements.

## Real Cube 3D Setup

CubeLite Studio expects users to install Cube 3D separately from official sources. In the Settings tab, set:

- local Cube 3D repo path
- local Cube 3D model weights path

CubeLite does not guess unstable Cube CLI flags. For real generation, add a `cubelite_cube_command.json` file to your local Cube 3D repo:

```json
{
  "command": ["{python}", "generate.py", "--prompt", "{prompt}", "--weights", "{weights_path}", "--output_dir", "{output_dir}"]
}
```

Only placeholders present in that template are passed to Cube 3D. Profile settings that are not supported by your Cube install remain CubeLite workflow notes or post-processing settings.

For the tested Roblox Cube 3D v0.5 setup, the Settings tab can write a CubeLite low-VRAM command template automatically. That template calls `app/cube/cubelite_low_vram_generate.py`, uses the Cube Python environment when it can detect one, and points at the official local weights selected in Settings.

## Model Weights Note

CubeLite Studio does not download, bundle, host, or redistribute Cube 3D model weights. Download model files only from official sources and follow the original Cube 3D license.

## Low-VRAM Modes

- `Benchmark Safe`: most conservative path for minimum viable testing, using a low Cube `resolution-base`.
- `Low VRAM`: targets 6GB to 8GB VRAM workflows with preview off, simplification on, and Cube `resolution-base` set low.
- `6GB Quality`: experimental push profile for 6GB GPUs that spends more VRAM with higher resolution, larger decode chunks, light guidance, and `top_p` sampling for candidate search.
- `Balanced`: targets 8GB to 12GB VRAM workflows with a midrange Cube `resolution-base`.
- `High Quality`: intended for 16GB+ GPUs; fast inference may require more VRAM and uses a higher Cube `resolution-base`.
- `Auto`: chooses a profile from detected VRAM.

These profiles are experimental workflow presets, not a guarantee that every Cube 3D release exposes every setting as a CLI flag.

CubeLite also includes `app/cube/cubelite_low_vram_generate.py`, a real low-VRAM Cube runner that can be used from a command template. It reduces VRAM pressure by keeping CLIP on CPU, disabling classifier-free guidance for the lowest profiles, avoiding KV cache, unloading GPT before shape decoding, and using a smaller decoder chunk size.

## Benchmarking

The benchmark runner tests a standard prompt set across selected profiles and records:

- prompt
- profile
- success or failure
- generation time
- peak VRAM if available
- output file size
- triangle count
- readiness score
- output path
- error message

Outputs are written to `benchmarks/` as CSV and JSON.

## Candidate Curation

Raw generation is not enough. CubeLite's curation runner generates multiple candidates, renders multi-angle inspection plates, scores mesh geometry, and writes a JSON plus Markdown curation report in `reports/`.

The curation score combines:

- heuristic Roblox-readiness
- triangle count and file size
- bounding-box proportions
- prompt-specific shape checks, such as box-like crates or elongated swords
- simplification health
- texture QA when material finishing succeeds
- render-plate visual checks for low-contrast, noisy, or mostly empty renders

Candidates are labeled `showcase_candidate`, `needs_review`, or `reject`. This is still not a semantic art judge, but it makes the workflow stricter: weak geometry should be rejected before it reaches a public example or Roblox import package.

## Style Presets

Style presets are used before generation and during material finishing. They add targeted prompt terms and steer the deterministic material provider:

- `Roblox Low Poly`: clean blocky props and restrained materials.
- `Toybox`: brighter rounded toy-like surfaces.
- `Hand Painted Fantasy`: warmer painted highlights and fantasy material cues.
- `Sci-Fi Plastic`: hard-surface panels and simple emissive accents.
- `Medieval Wood Metal`: wood grain, metal bands, and rivet-friendly materials.
- `Crystal Magic`: faceted crystal shapes and glow-like color accents.

The app shows the strengthened prompt before running so the rewrite is visible and editable.

## Roblox Export Workflow

Export packages are written to `exports/sanitized-prompt-timestamp/` and include:

- `original.obj`
- `optimized.obj` when simplification succeeds or a fallback copy exists
- `textured.obj`, `textured.mtl`, `albedo.png`, `normal.png`, `roughness.png`, and `metallic.png` when UV/texturing finishing succeeds
- `preview.png` when local rendering dependencies are available
- `inspection_plate.png` when multi-angle rendering succeeds
- `finish_report.json` with UV unwrap and texture generation details
- `metadata.json`
- `roblox_import_notes.txt`
- `benchmark_summary.json`

The readiness report is a heuristic helper, not official Roblox validation.

## Texture Providers

CubeLite has three texture providers:

- `studio`: default deterministic material generation for clean low-poly Roblox props.
- `procedural`: legacy fast atlas generation based on prompt keywords.
- `diffusers`: optional neural atlas generation through a local Hugging Face Diffusers model.

The default Diffusers model id is a tiny smoke-test model so automated tests can run quickly. For actual quality experiments, select a stronger local model such as `stable-diffusion-v1-5/stable-diffusion-v1-5` in the Settings tab or pass it to `run_texture_benchmark.py`.

The Diffusers path is a 2D texture-atlas provider, not a true 3D-aware texture painting system. It is useful for experiments and benchmarks, but generated textures still need inspection before Roblox use. The benchmark records provider, model id, dimensions, file size, contrast, color variance, production score, and warnings so texture runs can be compared with repeatable metadata.

## Example Outputs

Use dry-run mode to create an example export package immediately. This repo also includes a private example gallery in `sample_assets/real_cube_examples/` with real Cube 3D v0.5 outputs generated on an RTX 4050 Laptop GPU through CubeLite's low-VRAM path.

## Technical Report Generation

Benchmark runs can generate a Markdown report in `reports/` titled:

`CubeLite Studio: Low-VRAM Cube 3D Workflow Benchmark`

The report includes machine specs, setup notes, tested profiles, prompt set, results table, VRAM comparison notes, mesh complexity notes, limitations, and next steps.

The Case Study tab can also generate a portfolio-style Markdown and HTML pack from real local Cube 3D outputs in `sample_assets/real_cube_examples/`. This is meant for sharing the technical story: consumer-GPU bottleneck, low-VRAM staging approach, measured results, showcase outputs, mixed outputs, and honest limitations.

## Known Limitations

- Real Cube 3D generation requires the user to provide Cube 3D files and model weights.
- Command-line integration depends on a user-provided command template for the specific Cube release.
- VRAM telemetry depends on PyNVML or PyTorch CUDA support.
- Mesh simplification requires optional `pymeshlab`.
- UV unwrapping uses `xatlas`; neural texturing is optional and experimental, while the default studio provider generates deterministic material maps.
- Roblox readiness is heuristic and cannot guarantee import success.
- Dry run mode validates the pipeline but does not benchmark Cube 3D itself.

## License / Attribution

CubeLite Studio is independent. It does not own Cube 3D and does not redistribute Cube 3D model weights. Users are responsible for following the original Cube 3D license and Roblox platform rules.

See [LICENSE_NOTES.md](LICENSE_NOTES.md) for practical licensing and attribution notes.

## Disclaimer

CubeLite Studio is not affiliated with, endorsed by, or sponsored by Roblox Corporation. Roblox and related marks belong to their respective owners. This project is for experimentation, benchmarking, and creator workflow support.
