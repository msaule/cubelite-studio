# Outreach Email Draft

Subject: CubeLite Studio, a low-VRAM Cube 3D workflow study

Hi [Name],

I wanted to share a technical project I have been building around Roblox's open-source Cube 3D model.

The project is called CubeLite Studio. It is an independent local workflow for testing Cube 3D on consumer hardware. The main focus is not a GUI; it is measuring where local generation breaks, lowering peak VRAM enough to run on a 6GB laptop GPU, and packaging the resulting OBJ files in a way that is easier to inspect for Roblox-style use.

The useful result so far:

- On an RTX 4050 Laptop GPU with 6GB VRAM, the standard high-memory path hit CUDA out-of-memory at about 5.98GB peak usage.
- I built a staged runner that keeps CLIP text encoding on CPU, runs GPT token generation on GPU, unloads it, then loads the shape decoder separately.
- With that path, real Cube 3D v0.5 generations complete at roughly 3.93GB to 4.17GB observed peak VRAM.
- The app records time, peak VRAM, triangle count, file size, readiness notes, and failure reasons for each run.
- It also creates export folders with OBJ files, metadata, mesh previews, multi-angle render plates, and Roblox import notes.

The asset quality is still a work in progress. Some generated props are readable, and some are not good enough yet. I am treating that honestly in the case study by showing candidate search, multi-angle inspection, and failure cases instead of presenting every output as production-ready.

The project page is here:
[GitHub Pages or preview URL]

The repo is here:
[GitHub repo URL]

I would appreciate any feedback on whether this kind of low-VRAM benchmarking and creator-facing inspection/export workflow would be useful around Cube 3D. My goal is to make the practical hardware limits and asset-quality bottlenecks more visible for Roblox creators experimenting locally.

Best,
[Your Name]
