import os
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class DimensionInfo:
    id: str  # e.g., "minecraft:overworld", "twilightforest:twilightforest"
    name: str  # e.g., "Overworld", "Twilight Forest"
    region_dir: str  # absolute path to the directory containing .mca files

def format_dim_name(dim_id: str) -> str:
    """Format dimension ID into clean display name."""
    if dim_id == "minecraft:overworld":
        return "Overworld"
    elif dim_id == "minecraft:the_nether":
        return "The Nether"
    elif dim_id == "minecraft:the_end":
        return "The End"

    # Modded dimension e.g. "twilightforest:twilightforest" -> "Twilight Forest"
    parts = dim_id.split(":")
    name_part = parts[-1]
    cleaned = name_part.replace("_", " ").title()
    if len(parts) > 1 and parts[0] != "minecraft":
        mod_prefix = parts[0].replace("_", " ").title()
        if mod_prefix.lower() not in cleaned.lower():
            return f"{cleaned} ({mod_prefix})"
    return cleaned

def discover_dimensions(world_folder: str) -> List[DimensionInfo]:
    """
    Discover all dimensions (vanilla and modded) present in the world folder
    that have a region directory with .mca files.
    """
    dimensions: List[DimensionInfo] = []
    seen_paths = set()

    # 1. Overworld
    overworld_region = os.path.join(world_folder, "region")
    if os.path.isdir(overworld_region):
        dimensions.append(
            DimensionInfo(
                id="minecraft:overworld",
                name="Overworld",
                region_dir=overworld_region
            )
        )
        seen_paths.add(os.path.abspath(overworld_region))

    # 2. Nether
    nether_region = os.path.join(world_folder, "DIM-1", "region")
    if os.path.isdir(nether_region):
        dimensions.append(
            DimensionInfo(
                id="minecraft:the_nether",
                name="The Nether",
                region_dir=nether_region
            )
        )
        seen_paths.add(os.path.abspath(nether_region))

    # 3. The End
    end_region = os.path.join(world_folder, "DIM1", "region")
    if os.path.isdir(end_region):
        dimensions.append(
            DimensionInfo(
                id="minecraft:the_end",
                name="The End",
                region_dir=end_region
            )
        )
        seen_paths.add(os.path.abspath(end_region))

    # 4. Modded dimensions in 'dimensions/' folder
    dims_root = os.path.join(world_folder, "dimensions")
    if os.path.isdir(dims_root):
        for root, dirs, files in os.walk(dims_root):
            if "region" in dirs:
                reg_dir = os.path.join(root, "region")
                abs_reg_dir = os.path.abspath(reg_dir)
                if abs_reg_dir in seen_paths:
                    continue
                seen_paths.add(abs_reg_dir)

                # Compute dimension ID from relative path
                rel = os.path.relpath(root, dims_root)
                parts = rel.replace("\\", "/").split("/")
                if len(parts) >= 2:
                    dim_id = f"{parts[0]}:{parts[1]}"
                elif len(parts) == 1:
                    dim_id = f"{parts[0]}:{parts[0]}"
                else:
                    dim_id = f"custom:{os.path.basename(root)}"

                dimensions.append(
                    DimensionInfo(
                        id=dim_id,
                        name=format_dim_name(dim_id),
                        region_dir=reg_dir
                    )
                )

    return dimensions
