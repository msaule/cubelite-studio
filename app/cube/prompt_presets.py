PROMPT_PRESETS = [
    "a purple crystal blade fantasy sword with green gem accents, single object, ornate hilt, sharp blade, game asset",
    "a stylized low poly wooden row boat, single object, curved hull, simple game asset, clean silhouette",
    "lowpoly paper craft victorian rabbit, single character figurine, stylized toy, long ears, seated pose, clean silhouette",
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
        "Object-specific prompts from Cube's own examples can outperform generic Roblox checklist prompts.",
        "Single objects tend to work better than full scenes.",
        "Low-poly prompts are better aligned with Roblox import workflows.",
        "Simple geometry is easier to simplify, inspect, and import.",
        "Run multiple candidates for portfolio-quality assets; technical success is not the same as semantic quality.",
    ],
}
