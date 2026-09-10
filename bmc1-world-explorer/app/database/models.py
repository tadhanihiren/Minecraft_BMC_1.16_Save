"""Database schema definitions and SQL initialization."""

CREATE_TABLES_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS worlds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    seed TEXT,
    mc_version TEXT,
    spawn_x INTEGER,
    spawn_y INTEGER,
    spawn_z INTEGER,
    difficulty TEXT,
    game_type TEXT,
    is_forge INTEGER DEFAULT 1,
    last_scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scanned_regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    region_file TEXT NOT NULL,
    mtime REAL NOT NULL,
    size INTEGER NOT NULL,
    chunk_count INTEGER DEFAULT 0,
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(world_id) REFERENCES worlds(id) ON DELETE CASCADE,
    UNIQUE(world_id, dimension, region_file)
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    chunk_x INTEGER NOT NULL,
    chunk_z INTEGER NOT NULL,
    last_update INTEGER,
    dominant_biome_id TEXT,
    dominant_biome_name TEXT,
    FOREIGN KEY(world_id) REFERENCES worlds(id) ON DELETE CASCADE,
    UNIQUE(world_id, dimension, chunk_x, chunk_z)
);

CREATE TABLE IF NOT EXISTS spawners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    z INTEGER NOT NULL,
    chunk_x INTEGER NOT NULL,
    chunk_z INTEGER NOT NULL,
    source TEXT NOT NULL,
    confidence TEXT NOT NULL,
    FOREIGN KEY(world_id) REFERENCES worlds(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS structures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    structure_id TEXT NOT NULL,
    name TEXT NOT NULL,
    min_x INTEGER NOT NULL,
    max_x INTEGER NOT NULL,
    min_y INTEGER NOT NULL,
    max_y INTEGER NOT NULL,
    min_z INTEGER NOT NULL,
    max_z INTEGER NOT NULL,
    center_x INTEGER NOT NULL,
    center_y INTEGER NOT NULL,
    center_z INTEGER NOT NULL,
    chunk_x INTEGER NOT NULL,
    chunk_z INTEGER NOT NULL,
    source TEXT NOT NULL,
    confidence TEXT NOT NULL,
    FOREIGN KEY(world_id) REFERENCES worlds(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    chest_type TEXT NOT NULL,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    z INTEGER NOT NULL,
    chunk_x INTEGER NOT NULL,
    chunk_z INTEGER NOT NULL,
    loot_table TEXT,
    items_json TEXT,
    source TEXT NOT NULL,
    confidence TEXT NOT NULL,
    FOREIGN KEY(world_id) REFERENCES worlds(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ore_veins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    ore_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    center_x INTEGER NOT NULL,
    center_y INTEGER NOT NULL,
    center_z INTEGER NOT NULL,
    block_count INTEGER NOT NULL,
    min_x INTEGER NOT NULL,
    max_x INTEGER NOT NULL,
    min_y INTEGER NOT NULL,
    max_y INTEGER NOT NULL,
    min_z INTEGER NOT NULL,
    max_z INTEGER NOT NULL,
    chunk_x INTEGER NOT NULL,
    chunk_z INTEGER NOT NULL,
    FOREIGN KEY(world_id) REFERENCES worlds(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    mod_id TEXT NOT NULL,
    version TEXT,
    FOREIGN KEY(world_id) REFERENCES worlds(id) ON DELETE CASCADE,
    UNIQUE(world_id, mod_id)
);

CREATE TABLE IF NOT EXISTS completed_markers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    category TEXT NOT NULL,
    ref_id INTEGER NOT NULL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(world_id) REFERENCES worlds(id) ON DELETE CASCADE,
    UNIQUE(world_id, dimension, category, ref_id)
);

-- Spatial and lookup indexes for sub-millisecond query performance
CREATE INDEX IF NOT EXISTS idx_scanned_regions_lookup ON scanned_regions(world_id, dimension, region_file);
CREATE INDEX IF NOT EXISTS idx_chunks_dim_pos ON chunks(world_id, dimension, chunk_x, chunk_z);
CREATE INDEX IF NOT EXISTS idx_spawners_pos ON spawners(world_id, dimension, x, z);
CREATE INDEX IF NOT EXISTS idx_structures_pos ON structures(world_id, dimension, center_x, center_z);
CREATE INDEX IF NOT EXISTS idx_chests_pos ON chests(world_id, dimension, x, z);
CREATE INDEX IF NOT EXISTS idx_ore_veins_pos ON ore_veins(world_id, dimension, center_x, center_z);
CREATE INDEX IF NOT EXISTS idx_ore_veins_type ON ore_veins(world_id, dimension, ore_id);
"""
