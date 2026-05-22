# Real Cube 3D Examples

These examples were generated locally with official Roblox Cube 3D v0.5 weights using CubeLite Studio's experimental low-VRAM generator on an RTX 4050 Laptop GPU with 6GB VRAM.

The official Cube path initially failed with CUDA out-of-memory at about 5.98GB peak VRAM. The CubeLite low-VRAM path completed by:

- keeping CLIP text encoding on CPU
- disabling classifier-free guidance for the lowest-VRAM profile
- avoiding the GPT KV cache
- unloading GPT before shape decoding
- using `bfloat16`
- decoding geometry with a smaller chunk size

Benchmark summary:

- 3/3 successful real Cube generations
- average generation time: about 218 seconds
- peak observed VRAM: about 3.93GB
- readiness scores: 92/100 for each benchmark output

Additional quality pass:

- `low-poly-closed-wooden-treasure-chest-single-object-blocky-game-20260522-143807`
- generation time: about 211 seconds
- peak observed VRAM: about 3.93GB
- triangle count: 1,812
- readiness score: 92/100

These outputs are examples, not official Roblox validation. Users remain responsible for following the original Cube 3D license and Roblox platform rules.
