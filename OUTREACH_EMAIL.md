# Outreach Email Draft

Subject: CubeLite Studio: low-VRAM Cube 3D workflow case study

Hi [Name],

I wanted to share a small technical project I built around Roblox's open-source Cube 3D model.

The project is called CubeLite Studio. It is an independent local toolkit for testing Cube 3D on consumer hardware, with a focus on low-VRAM inference, benchmarking, mesh analysis, and Roblox-oriented export packaging. It does not redistribute Cube 3D weights and is not affiliated with Roblox.

The core result: on my RTX 4050 Laptop GPU with 6GB VRAM, the standard high-memory path hit CUDA out-of-memory near 5.98GB peak VRAM. I built a staged low-VRAM runner that keeps CLIP text encoding on CPU, runs GPT token generation on GPU, unloads GPT before shape decoding, and then loads the shape decoder separately. With that path, I completed real Cube 3D v0.5 generations at about 3.93GB to 4.17GB observed peak VRAM.

I also built the workflow around the model rather than only making a UI:

- Streamlit local app for generation, benchmarking, system checks, settings, and results
- Low-VRAM and 6GB Quality profiles
- VRAM/time/triangle-count tracking for each generation
- OBJ mesh analysis and optional pymeshlab simplification
- Roblox-readiness notes and export packages
- Case-study generator with screenshots, metrics, and curated successful/mixed/failure examples

One example: a 6GB Quality treasure chest run produced a 32,036-triangle mesh, then the export pipeline simplified it to 12,000 triangles with a 100/100 heuristic readiness score. I also generated a readable crate, fantasy sword, and row boat, while keeping some failed or mixed outputs in the report to show where the workflow still needs candidate search and cleanup.

The project page is here:
[GitHub Pages URL]

The private repo is here:
[GitHub repo URL]

I would be grateful for any feedback, especially on whether this kind of consumer-GPU benchmarking and creator-facing export workflow would be useful around Cube 3D. My goal was to treat Cube 3D as a real creator pipeline problem: measure practical bottlenecks, make failures visible, and turn raw mesh generation into something closer to a Roblox Studio import workflow.

Best,
[Your Name]
