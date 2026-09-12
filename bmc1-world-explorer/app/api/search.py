import re
from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any

from app.database.database import db
from app.api.worlds import active_world_state

router = APIRouter(prefix="/api/search", tags=["search"])

COORD_REGEX = re.compile(r"^\s*(-?\d+)\s*,\s*(-?\d+)(?:\s*,\s*(-?\d+))?\s*$")

@router.get("")
def global_search(
    query: str = Query(..., min_length=1),
    dimension: str = Query("minecraft:overworld"),
    limit: int = Query(50)
):
    world_id = active_world_state.get("world_id")
    if not world_id:
        return []

    # Check if query is coordinate format: X, Z or X, Y, Z
    match = COORD_REGEX.match(query)
    if match:
        x = int(match.group(1))
        if match.group(3) is not None:
            y = int(match.group(2))
            z = int(match.group(3))
        else:
            y = 64
            z = int(match.group(2))

        return [{
            "category": "coordinate",
            "name": f"Coordinate ({x}, {y}, {z})",
            "dimension": dimension,
            "x": x,
            "y": y,
            "z": z,
            "source": "Manual Search",
            "confidence": "HIGH"
        }]

    return db.search_features(world_id, dimension, query, limit=limit)

@router.get("/nearest")
def find_nearest_feature(
    feature_type: str = Query(..., pattern="^(ore|spawner|structure|biome)$"),
    subtype: Optional[str] = Query(None),
    x: int = Query(0),
    y: int = Query(64),
    z: int = Query(0),
    dimension: str = Query("minecraft:overworld"),
    max_distance: int = Query(50000)
):
    world_id = active_world_state.get("world_id")
    if not world_id:
        return None

    return db.find_nearest(
        world_id=world_id,
        dimension=dimension,
        feature_type=feature_type,
        subtype=subtype,
        current_x=x,
        current_y=y,
        current_z=z,
        max_distance=max_distance
    )
