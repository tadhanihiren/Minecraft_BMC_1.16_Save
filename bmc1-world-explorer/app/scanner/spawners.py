from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class SpawnerInfo:
    x: int
    y: int
    z: int
    entity_id: str
    display_name: str
    source: str
    confidence: str

def format_entity_name(entity_id: str) -> str:
    """Format entity ID like 'minecraft:skeleton' into 'Skeleton'."""
    clean = entity_id.split(":")[-1]
    return clean.replace("_", " ").title()

def extract_spawner(te: Dict[str, Any]) -> Optional[SpawnerInfo]:
    """
    Extract spawner information from a TileEntity compound tag.
    Returns SpawnerInfo or None if not a spawner.
    """
    te_id = te.get("id", "")
    if "spawner" not in te_id.lower():
        return None

    x = te.get("x")
    y = te.get("y")
    z = te.get("z")
    if x is None or y is None or z is None:
        return None

    entity_id = "Unknown"
    # 1. Check SpawnData
    spawn_data = te.get("SpawnData")
    if isinstance(spawn_data, dict):
        if "id" in spawn_data:
            entity_id = str(spawn_data["id"])
        elif "entity" in spawn_data and isinstance(spawn_data["entity"], dict) and "id" in spawn_data["entity"]:
            entity_id = str(spawn_data["entity"]["id"])

    # 2. Check SpawnPotentials
    if entity_id == "Unknown":
        potentials = te.get("SpawnPotentials")
        if isinstance(potentials, list) and potentials:
            first = potentials[0]
            if isinstance(first, dict):
                p_data = first.get("Entity") or first.get("data")
                if isinstance(p_data, dict) and "id" in p_data:
                    entity_id = str(p_data["id"])

    # 3. Check direct EntityId (older NBT format fallback)
    if entity_id == "Unknown" and "EntityId" in te:
        entity_id = str(te["EntityId"])

    if entity_id == "Unknown":
        display_name = "Unknown Spawner"
        confidence = "MEDIUM"
    else:
        display_name = f"{format_entity_name(entity_id)} Spawner"
        confidence = "HIGH"

    return SpawnerInfo(
        x=int(x),
        y=int(y),
        z=int(z),
        entity_id=entity_id,
        display_name=display_name,
        source="Generated Chunk NBT",
        confidence=confidence
    )
