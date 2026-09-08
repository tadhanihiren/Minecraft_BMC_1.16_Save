import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.scanner.level_parser import read_level_dat
from app.scanner.dimensions import discover_dimensions
from app.scanner.world_scanner import scanner
from app.database.database import db
from app.config import DEFAULT_WORLD_PATH

router = APIRouter(prefix="/api/worlds", tags=["worlds"])

# State for currently active world
active_world_state: Dict[str, Any] = {
    "world_id": None,
    "world_path": None,
    "world_name": "",
    "seed": None,
    "mc_version": "1.16.5",
    "dimensions": []
}

class WorldSelectRequest(BaseModel):
    path: str

class ScanStartRequest(BaseModel):
    force_rescan: bool = False
    dimension_id: Optional[str] = None

@router.post("/select")
def select_world(req: WorldSelectRequest):
    """Select and validate a Minecraft world folder."""
    path = os.path.abspath(req.path)
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail=f"Directory does not exist: {path}")

    level_dat = os.path.join(path, "level.dat")
    if not os.path.exists(level_dat):
        raise HTTPException(status_code=400, detail="Invalid Minecraft world: level.dat not found.")

    try:
        level_data = read_level_dat(path)
        spawn = level_data.spawn_coords
        world_id = db.upsert_world(
            path=path,
            name=level_data.world_name,
            seed=level_data.seed,
            mc_version=level_data.mc_version,
            spawn_x=spawn["x"],
            spawn_y=spawn["y"],
            spawn_z=spawn["z"],
            difficulty=level_data.difficulty,
            game_type=level_data.game_type,
            is_forge=level_data.is_forge
        )

        # Store installed mods
        mods = level_data.get_installed_mods()
        db.insert_mods_batch(world_id, mods)

        # Discovered dimensions
        dims = discover_dimensions(path)
        dims_list = [{"id": d.id, "name": d.name} for d in dims]

        active_world_state["world_id"] = world_id
        active_world_state["world_path"] = path
        active_world_state["world_name"] = level_data.world_name
        active_world_state["seed"] = level_data.seed
        active_world_state["mc_version"] = level_data.mc_version
        active_world_state["spawn"] = spawn
        active_world_state["difficulty"] = level_data.difficulty
        active_world_state["game_type"] = level_data.game_type
        active_world_state["is_forge"] = level_data.is_forge
        active_world_state["mods_count"] = len(mods)
        active_world_state["dimensions"] = dims_list

        return {
            "status": "success",
            "world": active_world_state
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading world: {e}")

@router.get("/current")
def get_current_world():
    """Get active world information."""
    if not active_world_state["world_path"]:
        if DEFAULT_WORLD_PATH and os.path.exists(DEFAULT_WORLD_PATH):
            try:
                select_world(WorldSelectRequest(path=DEFAULT_WORLD_PATH))
            except Exception:
                pass
    return active_world_state

@router.post("/scan/start")
def start_scan(req: ScanStartRequest):
    """Trigger background scanning of the active world."""
    if not active_world_state["world_path"]:
        raise HTTPException(status_code=400, detail="No world selected. Please select a world first.")

    started = scanner.start_scan(
        world_folder=active_world_state["world_path"],
        force_rescan=req.force_rescan,
        dimension_id=req.dimension_id
    )
    if not started:
        raise HTTPException(status_code=409, detail="A scan is already in progress.")

    return {"status": "started"}

@router.get("/scan/status")
def get_scan_status():
    """Get current scanning progress."""
    return scanner.get_progress()

@router.post("/scan/cancel")
def cancel_scan():
    """Cancel currently running scan."""
    scanner.cancel_scan()
    return {"status": "cancelled"}
