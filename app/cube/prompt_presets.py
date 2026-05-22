PROMPT_PRESETS = [
    "low poly fantasy sword, single object",
    "simple wooden crate, game asset",
    "cartoon mushroom house, small prop",
    "medieval shield with simple emblem",
    "sci-fi supply box, low poly",
    "cute dragon pet toy, stylized",
    "pirate treasure chest, simple geometry",
    "magic potion bottle, stylized game prop",
    "simple castle tower, low poly",
    "stylized tree stump, single object",
    "small market stall, simplified prop",
    "ancient stone archway, low poly",
    "glowing crystal cluster, stylized",
    "toy robot character, simple shape",
    "wooden sign post, game-ready prop",
]

PROMPT_GUIDANCE = {
    "good": "low poly wooden treasure chest, single object, simple geometry, game asset",
    "bad": "huge ultra detailed medieval city with thousands of buildings and tiny decorations",
    "notes": [
        "Single objects tend to work better than full scenes.",
        "Low-poly prompts are better aligned with Roblox import workflows.",
        "Simple geometry is easier to simplify, inspect, and import.",
        "Avoid extremely detailed prompts when using low-VRAM mode.",
    ],
}
