from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass
class StructureInfo:
    structure_id: str
    name: str
    min_x: int
    max_x: int
    min_y: int
    max_y: int
    min_z: int
    max_z: int
    center_x: int
    center_y: int
    center_z: int
    chunk_x: int
    chunk_z: int
    source: str
    confidence: str

def format_structure_name(struct_id: str, orig_name: str) -> str:
    """Format structure ID into clean display name."""
    clean = struct_id.replace("minecraft:", "")
    parts = clean.split(":")
    if len(parts) > 1:
        mod = parts[0].replace("_", " ").title()
        name = parts[1].replace("_", " ").title()
        return f"{name} ({mod})"
    return clean.replace("_", " ").title()

def extract_structures_from_chunk(
    chunk_root: Dict[str, Any],
    chunk_x: int,
    chunk_z: int
) -> List[StructureInfo]:
    """
    Extract confirmed structure starts from chunk NBT data.
    Only structures actually present with valid bounding boxes are returned.
    """
    level = chunk_root.get("Level", {})
    structures_tag = level.get("Structures")
    if not isinstance(structures_tag, dict):
        return []

    starts = structures_tag.get("Starts")
    if not isinstance(starts, dict):
        return []

    results: List[StructureInfo] = []

    for name_key, sdata in starts.items():
        if not isinstance(sdata, dict):
            continue

        sid = sdata.get("id")
        if not sid or str(sid).upper() == "INVALID":
            continue

        bb = sdata.get("BB")
        # In Minecraft NBT, BB is an IntArray or List of 6 integers: [min_x, min_y, min_z, max_x, max_y, max_z]
        if not bb or len(bb) < 6:
            continue

        min_x, min_y, min_z, max_x, max_y, max_z = [int(v) for v in bb[:6]]

        # Ensure min <= max
        if min_x > max_x:
            min_x, max_x = max_x, min_x
        if min_y > max_y:
            min_y, max_y = max_y, min_y
        if min_z > max_z:
            min_z, max_z = max_z, min_z

        center_x = (min_x + max_x) // 2
        center_y = (min_y + max_y) // 2
        center_z = (min_z + max_z) // 2

        display_name = format_structure_name(str(sid), name_key)

        results.append(
            StructureInfo(
                structure_id=str(sid),
                name=display_name,
                min_x=min_x,
                max_x=max_x,
                min_y=min_y,
                max_y=max_y,
                min_z=min_z,
                max_z=max_z,
                center_x=center_x,
                center_y=center_y,
                center_z=center_z,
                chunk_x=chunk_x,
                chunk_z=chunk_z,
                source="Generated Chunk NBT",
                confidence="HIGH"
            )
        )

    return results
