from typing import List, Dict, Any, Optional, Tuple
from collections import Counter

# Standard vanilla 1.16.5 biome ID map fallback
VANILLA_BIOMES: Dict[int, str] = {
    0: "minecraft:ocean",
    1: "minecraft:plains",
    2: "minecraft:desert",
    3: "minecraft:mountains",
    4: "minecraft:forest",
    5: "minecraft:taiga",
    6: "minecraft:swamp",
    7: "minecraft:river",
    8: "minecraft:nether_wastes",
    9: "minecraft:the_end",
    10: "minecraft:frozen_ocean",
    11: "minecraft:frozen_river",
    12: "minecraft:snowy_tundra",
    13: "minecraft:snowy_mountains",
    14: "minecraft:mushroom_fields",
    15: "minecraft:mushroom_field_shore",
    16: "minecraft:beach",
    17: "minecraft:desert_hills",
    18: "minecraft:wooded_hills",
    19: "minecraft:taiga_hills",
    20: "minecraft:mountain_edge",
    21: "minecraft:jungle",
    22: "minecraft:jungle_hills",
    23: "minecraft:jungle_edge",
    24: "minecraft:deep_ocean",
    25: "minecraft:stone_shore",
    26: "minecraft:snowy_beach",
    27: "minecraft:birch_forest",
    28: "minecraft:birch_forest_hills",
    29: "minecraft:dark_forest",
    30: "minecraft:snowy_taiga",
    31: "minecraft:snowy_taiga_hills",
    32: "minecraft:giant_tree_taiga",
    33: "minecraft:giant_tree_taiga_hills",
    34: "minecraft:wooded_mountains",
    35: "minecraft:savanna",
    36: "minecraft:savanna_plateau",
    37: "minecraft:badlands",
    38: "minecraft:wooded_badlands_plateau",
    39: "minecraft:badlands_plateau",
    40: "minecraft:small_end_islands",
    41: "minecraft:end_midlands",
    42: "minecraft:end_highlands",
    43: "minecraft:end_barrens",
    44: "minecraft:warm_ocean",
    45: "minecraft:lukewarm_ocean",
    46: "minecraft:cold_ocean",
    47: "minecraft:deep_warm_ocean",
    48: "minecraft:deep_lukewarm_ocean",
    49: "minecraft:deep_cold_ocean",
    50: "minecraft:deep_frozen_ocean",
    127: "minecraft:the_void",
    129: "minecraft:sunflower_plains",
    130: "minecraft:desert_lakes",
    131: "minecraft:gravelly_mountains",
    132: "minecraft:flower_forest",
    133: "minecraft:taiga_mountains",
    134: "minecraft:swamp_hills",
    140: "minecraft:ice_spikes",
    149: "minecraft:modified_jungle",
    151: "minecraft:modified_jungle_edge",
    155: "minecraft:tall_birch_forest",
    156: "minecraft:tall_birch_hills",
    157: "minecraft:dark_forest_hills",
    158: "minecraft:snowy_taiga_mountains",
    160: "minecraft:giant_spruce_taiga",
    161: "minecraft:giant_spruce_taiga_hills",
    162: "minecraft:modified_gravelly_mountains",
    163: "minecraft:shattered_savanna",
    164: "minecraft:shattered_savanna_plateau",
    165: "minecraft:eroded_badlands",
    166: "minecraft:modified_wooded_badlands_plateau",
    167: "minecraft:modified_badlands_plateau",
    168: "minecraft:bamboo_jungle",
    169: "minecraft:bamboo_jungle_hills",
    170: "minecraft:soul_sand_valley",
    171: "minecraft:crimson_forest",
    172: "minecraft:warped_forest",
    173: "minecraft:basalt_deltas"
}

def format_biome_name(biome_id: str) -> str:
    """Format biome ID like 'byg:jacaranda_forest' into 'Jacaranda Forest'."""
    clean = biome_id.replace("minecraft:", "")
    parts = clean.split(":")
    if len(parts) > 1:
        mod = parts[0].replace("_", " ").upper()
        name = parts[1].replace("_", " ").title()
        return f"{name} ({mod})"
    return clean.replace("_", " ").title()

def resolve_biome_id(int_id: int, registry_map: Optional[Dict[int, str]] = None) -> str:
    """Resolve an integer biome ID to canonical string."""
    if registry_map and int_id in registry_map:
        return registry_map[int_id]
    if int_id in VANILLA_BIOMES:
        return VANILLA_BIOMES[int_id]
    return f"unknown:biome_{int_id}"

def extract_chunk_biomes(
    chunk_root: Dict[str, Any],
    registry_map: Optional[Dict[int, str]] = None
) -> Tuple[str, str]:
    """
    Extract dominant biome from chunk 1.16.5 NBT.
    Returns (dominant_biome_id, dominant_biome_name).
    """
    level = chunk_root.get("Level", {})
    biomes_data = level.get("Biomes")
    if not biomes_data or not isinstance(biomes_data, list):
        return "minecraft:plains", "Plains"

    # Count occurrences
    counts = Counter(biomes_data)
    most_common_id, _ = counts.most_common(1)[0]
    canonical_id = resolve_biome_id(most_common_id, registry_map)
    display_name = format_biome_name(canonical_id)
    return canonical_id, display_name
