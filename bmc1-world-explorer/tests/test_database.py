import pytest
import os
import tempfile
import json
from pathlib import Path
from app.database.database import Database

import gc

@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test_explorer.db"
        test_database = Database(db_path)
        yield test_database
        test_database.close()
        gc.collect()

def test_database_single_file_and_ops(temp_db):
    # Test world upsert
    world_id = temp_db.upsert_world(
        path="C:/test/world",
        name="Test World",
        seed=123456789,
        mc_version="1.16.5",
        spawn_x=100,
        spawn_y=64,
        spawn_z=-200,
        difficulty="Normal",
        game_type="Survival"
    )
    assert world_id > 0

    # Insert sample spawner
    temp_db.insert_spawners_batch([
        (world_id, "minecraft:overworld", "minecraft:zombie", "Zombie Spawner", 124, 34, -582, 7, -37, "Generated Chunk NBT", "HIGH"),
        (world_id, "minecraft:overworld", "minecraft:skeleton", "Skeleton Spawner", 500, 20, 500, 31, 31, "Generated Chunk NBT", "HIGH")
    ])

    # Insert sample ore vein
    temp_db.insert_ore_veins_batch([
        (world_id, "minecraft:overworld", "minecraft:diamond_ore", "Diamond Ore", 125, 12, -583, 8, 124, 126, 11, 13, -584, -582, 7, -37),
        (world_id, "minecraft:overworld", "minecraft:iron_ore", "Iron Ore", 0, 40, 0, 15, -1, 1, 39, 41, -1, 1, 0, 0)
    ])

    # Query markers with filters
    markers = temp_db.get_markers(world_id, "minecraft:overworld", include_ores=True, include_spawners=True)
    assert len(markers) == 4

    # Test nearest search
    # At (120, 64, -580), nearest spawner should be the Zombie spawner at (124, -582)
    nearest_spawner = temp_db.find_nearest(
        world_id=world_id,
        dimension="minecraft:overworld",
        feature_type="spawner",
        subtype=None,
        current_x=120,
        current_y=64,
        current_z=-580
    )
    assert nearest_spawner is not None
    assert "Zombie" in nearest_spawner["name"]
    assert nearest_spawner["distance"] < 10

    # Test nearest diamond
    nearest_ore = temp_db.find_nearest(
        world_id=world_id,
        dimension="minecraft:overworld",
        feature_type="ore",
        subtype="diamond",
        current_x=120,
        current_y=64,
        current_z=-580
    )
    assert nearest_ore is not None
    assert "Diamond" in nearest_ore["name"]
    assert nearest_ore["x"] == 125

    # Test search features
    search_res = temp_db.search_features(world_id, "minecraft:overworld", "diamond")
    assert len(search_res) >= 1

    # Test Git export JSON
    export_path = os.path.join(os.path.dirname(temp_db.db_path), "git_dump.json")
    temp_db.export_all_json(world_id, export_path)
    assert os.path.exists(export_path)
    with open(export_path, "r") as f:
        dump_data = json.load(f)
    assert "stats" in dump_data
    assert len(dump_data["spawners"]) == 2

    # Test WAL checkpoint to guarantee single-file completeness
    temp_db.checkpoint()
    assert os.path.exists(temp_db.db_path)
