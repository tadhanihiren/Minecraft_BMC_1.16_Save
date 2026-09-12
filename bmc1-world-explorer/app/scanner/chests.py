from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import json

@dataclass
class ChestItem:
    id: str
    count: int
    slot: int

@dataclass
class ChestInfo:
    x: int
    y: int
    z: int
    chest_type: str
    loot_table: Optional[str]
    items: List[ChestItem]
    source: str
    confidence: str

def format_item_name(item_id: str) -> str:
    parts = item_id.split(":")[-1].replace("_", " ").title()
    return parts

def extract_chest(te: Dict[str, Any]) -> Optional[ChestInfo]:
    """
    Extract chest/inventory block entity data.
    Supports vanilla chests, barrels, trapped chests, shulker boxes, and modded equivalents.
    """
    te_id = te.get("id", "")
    te_id_lower = te_id.lower()
    is_container = any(
        k in te_id_lower for k in ("chest", "barrel", "shulker_box", "dispenser", "dropper", "hopper")
    )
    if not is_container:
        return None

    x = te.get("x")
    y = te.get("y")
    z = te.get("z")
    if x is None or y is None or z is None:
        return None

    loot_table = te.get("LootTable")
    if loot_table is not None:
        loot_table = str(loot_table)

    raw_items = te.get("Items", [])
    items: List[ChestItem] = []
    if isinstance(raw_items, list):
        for item in raw_items:
            if isinstance(item, dict):
                iid = str(item.get("id", "minecraft:air"))
                cnt = int(item.get("Count", 1))
                slot = int(item.get("Slot", 0))
                items.append(ChestItem(id=iid, count=cnt, slot=slot))

    return ChestInfo(
        x=int(x),
        y=int(y),
        z=int(z),
        chest_type=te_id,
        loot_table=loot_table,
        items=items,
        source="Generated Chunk NBT",
        confidence="HIGH"
    )
