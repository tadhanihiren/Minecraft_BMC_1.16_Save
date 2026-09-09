import pytest
from app.scanner.spawners import extract_spawner
from app.scanner.ores import cluster_ore_veins
from app.scanner.biomes import resolve_biome_id, format_biome_name

def test_extract_spawner():
    # 1. Zombie spawner
    te_zombie = {
        "id": "minecraft:mob_spawner",
        "x": 100,
        "y": 30,
        "z": -200,
        "SpawnData": {"id": "minecraft:zombie"}
    }
    s = extract_spawner(te_zombie)
    assert s is not None
    assert s.entity_id == "minecraft:zombie"
    assert s.display_name == "Zombie Spawner"
    assert s.confidence == "HIGH"
    assert s.x == 100
    assert s.y == 30
    assert s.z == -200

    # 2. Skeleton spawner
    te_skel = {
        "id": "minecraft:mob_spawner",
        "x": 50,
        "y": 40,
        "z": -100,
        "SpawnData": {"id": "minecraft:skeleton"}
    }
    s = extract_spawner(te_skel)
    assert s is not None
    assert s.entity_id == "minecraft:skeleton"
    assert s.display_name == "Skeleton Spawner"

    # 3. Spider spawner via SpawnPotentials
    te_spider = {
        "id": "minecraft:mob_spawner",
        "x": 0,
        "y": 20,
        "z": 0,
        "SpawnPotentials": [{"Entity": {"id": "minecraft:spider"}}]
    }
    s = extract_spawner(te_spider)
    assert s is not None
    assert s.entity_id == "minecraft:spider"
    assert s.display_name == "Spider Spawner"

    # 4. Unknown spawner
    te_unknown = {
        "id": "minecraft:mob_spawner",
        "x": 10,
        "y": 15,
        "z": 10
    }
    s = extract_spawner(te_unknown)
    assert s is not None
    assert s.display_name == "Unknown Spawner"
    assert s.confidence == "MEDIUM"

    # 5. Non-spawner
    te_chest = {"id": "minecraft:chest", "x": 1, "y": 1, "z": 1}
    assert extract_spawner(te_chest) is None

def test_cluster_ore_veins():
    # 3 adjacent diamond ore blocks
    blocks = [
        ("minecraft:diamond_ore", 100, 12, 200),
        ("minecraft:diamond_ore", 100, 13, 200),
        ("minecraft:diamond_ore", 101, 12, 200),
        # 1 isolated diamond ore block far away
        ("minecraft:diamond_ore", 500, 12, 500),
        # 1 iron ore block right next to diamond
        ("minecraft:iron_ore", 100, 12, 201),
    ]

    veins = cluster_ore_veins(blocks)
    assert len(veins) == 3

    # Check diamond vein 1
    d_vein = next(v for v in veins if v.ore_id == "minecraft:diamond_ore" and v.block_count == 3)
    assert d_vein.block_count == 3
    assert d_vein.min_x == 100 and d_vein.max_x == 101

    # Check isolated diamond vein
    iso_vein = next(v for v in veins if v.ore_id == "minecraft:diamond_ore" and v.block_count == 1)
    assert iso_vein.center_x == 500

    # Check iron vein (separate type)
    iron_vein = next(v for v in veins if v.ore_id == "minecraft:iron_ore")
    assert iron_vein.block_count == 1

def test_biome_resolution():
    # Vanilla biome
    assert resolve_biome_id(1) == "minecraft:plains"
    assert format_biome_name("minecraft:plains") == "Plains"

    # Modded registry biome
    fml_reg = {150: "byg:jacaranda_forest", 345: "twilightforest:forest"}
    assert resolve_biome_id(150, fml_reg) == "byg:jacaranda_forest"
    assert "Jacaranda Forest" in format_biome_name("byg:jacaranda_forest")
    assert resolve_biome_id(345, fml_reg) == "twilightforest:forest"
