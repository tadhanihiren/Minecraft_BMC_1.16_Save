from fastapi import APIRouter
from app.database.database import db
from app.api.worlds import active_world_state

router = APIRouter(prefix="/api/stats", tags=["stats"])

@router.get("")
def get_stats():
    world_id = active_world_state.get("world_id")
    if not world_id:
        return {}
    return db.get_world_stats(world_id)
