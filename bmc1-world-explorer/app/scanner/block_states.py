from typing import List, Dict, Any, Tuple, Generator

ALLOWED_ORE_IDS = {
    "minecraft:lapis_ore",
    "minecraft:diamond_ore",
    "cavesandcliffs:deepslate_diamond_ore",
    "darkerdepths:silver_ore",
    "minecraft:nether_gold_ore",
    "cavesandcliffs:spore_blossom",
    "savageandravage:spore_bomb",
    "morevillagers:woodworking_table",
    "morevillagers:gardening_table",
    "morevillagers:oceanography_table",
    "morevillagers:hunting_post",
}

def is_ore_block(block_name: str) -> bool:
    """Determine if a block identifier is in the tracked allow-list."""
    return block_name in ALLOWED_ORE_IDS

def find_ores_in_section(
    section: Dict[str, Any],
    chunk_x: int,
    chunk_z: int,
    section_y: int
) -> List[Tuple[str, int, int, int]]:
    """
    Fast extraction of ore blocks from a 1.16.5 chunk section.
    Returns list of (ore_name, block_x, block_y, block_z).
    """
    palette = section.get("Palette")
    if not palette or not isinstance(palette, list):
        return []

    # Map palette index to block name
    palette_names = [p.get("Name", "") if isinstance(p, dict) else "" for p in palette]

    # Quick check: does the palette contain ANY ores?
    ore_palette_indices = {
        idx: name for idx, name in enumerate(palette_names) if is_ore_block(name)
    }
    if not ore_palette_indices:
        return []

    # Single-block section (all 4096 blocks are the same)
    if len(palette) == 1:
        ore_name = palette_names[0]
        base_x = chunk_x * 16
        base_y = section_y * 16
        base_z = chunk_z * 16
        results = []
        for ly in range(16):
            for lz in range(16):
                for lx in range(16):
                    results.append((ore_name, base_x + lx, base_y + ly, base_z + lz))
        return results

    block_states = section.get("BlockStates")
    if not block_states or not isinstance(block_states, list):
        return []

    bits_per_block = max(4, (len(palette) - 1).bit_length())
    indices_per_long = 64 // bits_per_block
    mask = (1 << bits_per_block) - 1

    base_x = chunk_x * 16
    base_y = section_y * 16
    base_z = chunk_z * 16

    results: List[Tuple[str, int, int, int]] = []
    num_longs = len(block_states)

    # Convert signed longs to unsigned 64-bit ints
    u_longs = [val & 0xFFFFFFFFFFFFFFFF for val in block_states]

    for index in range(4096):
        long_idx = index // indices_per_long
        if long_idx >= num_longs:
            break
        bit_shift = (index % indices_per_long) * bits_per_block
        palette_idx = (u_longs[long_idx] >> bit_shift) & mask

        if palette_idx in ore_palette_indices:
            ore_name = ore_palette_indices[palette_idx]
            local_y = (index >> 8) & 0xF
            local_z = (index >> 4) & 0xF
            local_x = index & 0xF
            results.append((
                ore_name,
                base_x + local_x,
                base_y + local_y,
                base_z + local_z
            ))

    return results
