# CubeLite Studio Product Brief

CubeLite Studio is an independent local workflow around Roblox Cube 3D. It is built for Roblox creators who want to test text-to-3D generation on consumer hardware, see real VRAM and mesh data, and get a cleaner folder they can try in Roblox Studio.

This project does not redistribute Cube 3D weights and is not affiliated with, sponsored by, or endorsed by Roblox Corporation.

## The Problem

Cube 3D is promising for creator workflows, but the practical path from prompt to Roblox Studio is still rough:

- many creators have 6GB to 12GB GPUs, not workstation cards
- failed runs often do not explain whether VRAM, prompt shape, or mesh complexity caused the issue
- raw OBJ output still needs inspection, cleanup, material work, and packaging
- public examples can look better than the average local result, which makes hardware expectations unclear

## What CubeLite Adds

- a local Streamlit app for generation, settings, diagnostics, benchmarks, and results
- a staged low-VRAM runner for real Cube 3D v0.5 testing
- VRAM, timing, triangle count, file size, and readiness telemetry
- multi-seed candidate curation instead of treating the first output as final
- prompt-specific geometry scoring, including sword-vs-dagger checks
- mesh finishing with UV unwrap, material maps, and repair/rebuild templates
- export packages with a clearly named `roblox_import_this.obj`
- an `asset_readme.md` in each export folder for quick review
- a GitHub Pages case-study page with real local outputs and measured limits

## Current Evidence

Test machine:

- GPU: RTX 4050 Laptop GPU, 6GB VRAM
- Official-style high-memory path: hit CUDA out-of-memory around 5.98GB
- CubeLite low-VRAM real runs: completed at about 3.93GB to 4.17GB peak observed VRAM

Current rebuilt longsword artifact:

- Readiness: 100/100 heuristic score
- Triangles: 742
- Vertices: 495
- Export folder includes OBJ, MTL, inspection plate, metadata, Roblox notes, and asset README

The readiness score is not official Roblox validation. It is a practical checklist for first-pass Roblox Studio testing.

## Why It Matters

CubeLite is not trying to replace Cube 3D. It shows how a creator-facing workflow could make Cube 3D easier to evaluate:

- clearer hardware expectations
- less guesswork after failed runs
- better separation between raw generation and reviewable assets
- local-only workflow with no private Roblox credentials
- repeatable benchmark data instead of anecdotal screenshots

## What Still Needs Work

- broader testing across more GPUs
- more repair templates beyond swords and simple props
- better material transfer into Roblox Studio
- in-engine import validation and scale checks
- a stronger 3D renderer for final preview images

## Suggested Demo Flow

1. Open the local app.
2. Show System Check and detected GPU/VRAM.
3. Run or load a Cube 3D candidate search.
4. Show the curation report and reject reasons.
5. Open the export folder.
6. Import `roblox_import_this.obj` into Roblox Studio.
7. Show metadata, import notes, and benchmark results.

