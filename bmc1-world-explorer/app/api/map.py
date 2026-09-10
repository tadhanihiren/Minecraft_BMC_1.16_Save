from fastapi import APIRouter, Query, Body
from typing import Optional, List, Dict, Any

from app.database.database import db
from app.api.worlds import active_world_state

router = APIRouter(prefix="/api/map", tags=["map"])

@router.get("/markers")
def get_map_markers(
    dimension: str = Query("minecraft:overworld"),
    min_x: Optional[int] = Query(None),
    max_x: Optional[int] = Query(None),
    min_z: Optional[int] = Query(None),
    max_z: Optional[int] = Query(None),
    include_ores: bool = Query(True),
    include_spawners: bool = Query(True),
    include_structures: bool = Query(True),
    include_chests: bool = Query(True),
    ores: Optional[str] = Query(None),
    spawners: Optional[str] = Query(None),
    structures: Optional[str] = Query(None),
    limit: int = Query(3000)
):
    world_id = active_world_state.get("world_id")
    if not world_id:
        return []

    ore_filter = [o.strip() for o in ores.split(",") if o.strip()] if ores else None
    spawner_filter = [s.strip() for s in spawners.split(",") if s.strip()] if spawners else None
    structure_filter = [st.strip() for st in structures.split(",") if st.strip()] if structures else None

    return db.get_markers(
        world_id=world_id,
        dimension=dimension,
        min_x=min_x,
        max_x=max_x,
        min_z=min_z,
        max_z=max_z,
        include_ores=include_ores,
        include_spawners=include_spawners,
        include_structures=include_structures,
        include_chests=include_chests,
        ore_filter=ore_filter,
        spawner_filter=spawner_filter,
        structure_filter=structure_filter,
        limit=limit
    )

@router.post("/markers/complete")
def toggle_marker_completed(
    dimension: str = Body(...),
    category: str = Body(...),
    ref_id: int = Body(...)
):
    """Flip a marker's completed (mined/looted/cleared) state."""
    world_id = active_world_state.get("world_id")
    if not world_id:
        return {"completed": False}
    completed = db.toggle_completed(world_id, dimension, category, ref_id)
    return {"completed": completed}

@router.get("/biomes")
def get_map_biomes(
    dimension: str = Query("minecraft:overworld"),
    min_x: Optional[int] = Query(None),
    max_x: Optional[int] = Query(None),
    min_z: Optional[int] = Query(None),
    max_z: Optional[int] = Query(None),
):
    world_id = active_world_state.get("world_id")
    if not world_id:
        return []

    min_chunk_x = min_chunk_z = max_chunk_x = max_chunk_z = None
    if min_x is not None:
        min_chunk_x, max_chunk_x = min_x >> 4, max_x >> 4
        min_chunk_z, max_chunk_z = min_z >> 4, max_z >> 4

    return db.get_chunk_biomes(
        world_id, dimension,
        min_chunk_x=min_chunk_x, max_chunk_x=max_chunk_x,
        min_chunk_z=min_chunk_z, max_chunk_z=max_chunk_z
    )

@router.get("/filter_options")
def get_filter_options(dimension: str = Query("minecraft:overworld")):
    """Get list of distinct ore, spawner, and structure types found in this dimension."""
    world_id = active_world_state.get("world_id")
    if not world_id:
        return {"ores": [], "spawners": [], "structures": []}

    with db.get_connection() as conn:
        ore_rows = conn.execute(
            "SELECT DISTINCT ore_id, display_name FROM ore_veins WHERE world_id = ? AND dimension = ? ORDER BY display_name",
            (world_id, dimension)
        ).fetchall()
        spawner_rows = conn.execute(
            "SELECT DISTINCT entity_id, display_name FROM spawners WHERE world_id = ? AND dimension = ? ORDER BY display_name",
            (world_id, dimension)
        ).fetchall()
        struct_rows = conn.execute(
            "SELECT DISTINCT structure_id, name FROM structures WHERE world_id = ? AND dimension = ? ORDER BY name",
            (world_id, dimension)
        ).fetchall()

        return {
            "ores": [{"id": r["ore_id"], "name": r["display_name"]} for r in ore_rows],
            "spawners": [{"id": r["entity_id"], "name": r["display_name"]} for r in spawner_rows],
            "structures": [{"id": r["structure_id"], "name": r["name"]} for r in struct_rows]
        }
