import os
from fastapi import APIRouter

from app.database.database import db
from app.api.worlds import active_world_state
from app.config import DATA_DIR

router = APIRouter(prefix="/api/export", tags=["export"])

@router.post("/git_dump")
def dump_for_git():
    """Create or update world_data.json in bmc1-world-explorer/data/ for Git tracking."""
    world_id = active_world_state.get("world_id")
    if not world_id:
        return {"status": "error", "message": "No world selected"}

    db.checkpoint()  # Flush SQLite WAL into main .db file
    dump_path = os.path.join(DATA_DIR, "world_data.json")
    db.export_all_json(world_id, dump_path)

    return {
        "status": "success",
        "message": f"Saved Git dump to {dump_path} and flushed single SQLite file.",
        "db_file": str(db.db_path),
        "json_dump": dump_path
    }
