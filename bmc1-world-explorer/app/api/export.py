import csv
import io
import json
import os
from fastapi import APIRouter, Query, Response
from fastapi.responses import StreamingResponse, FileResponse
from typing import Optional

from app.database.database import db
from app.api.worlds import active_world_state
from app.config import DATA_DIR

router = APIRouter(prefix="/api/export", tags=["export"])

@router.get("/csv")
def export_csv(
    category: str = Query("all", pattern="^(spawners|structures|chests|ores|all)$"),
    dimension: str = Query("minecraft:overworld")
):
    """Export filtered world features as CSV."""
    world_id = active_world_state.get("world_id")
    if not world_id:
        return Response(content="No world selected", status_code=400)

    include_ores = category in ("ores", "all")
    include_spawners = category in ("spawners", "all")
    include_structures = category in ("structures", "all")
    include_chests = category in ("chests", "all")

    markers = db.get_markers(
        world_id=world_id,
        dimension=dimension,
        include_ores=include_ores,
        include_spawners=include_spawners,
        include_structures=include_structures,
        include_chests=include_chests,
        limit=50000
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Category", "Type", "Name", "Dimension", "X", "Y", "Z", "Source", "Confidence", "Extra"])

    for m in markers:
        extra = ""
        if m["category"] == "ore":
            extra = f"Blocks: {m.get('blocks', 1)}"
        elif m["category"] == "chest":
            items = m.get("items", [])
            extra = f"LootTable: {m.get('loot_table', '')}; Items: {len(items)}"
        elif m["category"] == "structure":
            extra = f"BBox: {m.get('bbox', [])}"

        writer.writerow([
            m["category"],
            m.get("type", ""),
            m.get("name", ""),
            dimension,
            m["x"],
            m["y"],
            m["z"],
            m.get("source", "Generated Chunk NBT"),
            m.get("confidence", "HIGH"),
            extra
        ])

    output.seek(0)
    filename = f"bmc1_{category}_{dimension.replace(':', '_')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/json")
def export_json(dimension: str = Query("minecraft:overworld")):
    """Export world markers as JSON file."""
    world_id = active_world_state.get("world_id")
    if not world_id:
        return Response(content="No world selected", status_code=400)

    markers = db.get_markers(
        world_id=world_id,
        dimension=dimension,
        include_ores=True,
        include_spawners=True,
        include_structures=True,
        include_chests=True,
        limit=50000
    )

    data = {
        "world": active_world_state.get("world_name"),
        "seed": active_world_state.get("seed"),
        "dimension": dimension,
        "features_count": len(markers),
        "features": markers
    }

    content = json.dumps(data, indent=2)
    filename = f"bmc1_world_data_{dimension.replace(':', '_')}.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

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
