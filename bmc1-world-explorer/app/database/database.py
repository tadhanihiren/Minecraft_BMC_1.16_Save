import sqlite3
import json
import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from app.config import DATABASE_PATH
from app.database.models import CREATE_TABLES_SQL

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = str(db_path)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        # Enable foreign keys and optimize performance
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        # A world with a million-plus ore rows benefits from a bigger page
        # cache and memory-mapped reads — avoids a disk syscall per page
        # on repeated bbox queries while panning the map.
        conn.execute("PRAGMA cache_size = -64000;")  # 64MB page cache
        conn.execute("PRAGMA temp_store = MEMORY;")
        conn.execute("PRAGMA mmap_size = 268435456;")  # 256MB
        return conn

    def init_db(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self.get_connection() as conn:
            conn.executescript(CREATE_TABLES_SQL)
            conn.commit()

    def checkpoint(self) -> None:
        """
        Flush WAL into the main single .db file so that the single .db file
        contains all data and can be copied / uploaded to Git without missing writes.
        """
        try:
            with self.get_connection() as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to checkpoint SQLite WAL: {e}")

    def close(self) -> None:
        """Checkpoint and ensure database handles are released."""
        self.checkpoint()

    # --- Worlds ---
    def upsert_world(
        self,
        path: str,
        name: str,
        seed: Optional[int],
        mc_version: str,
        spawn_x: int,
        spawn_y: int,
        spawn_z: int,
        difficulty: str,
        game_type: str,
        is_forge: bool = True
    ) -> int:
        norm_path = os.path.abspath(path)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO worlds (path, name, seed, mc_version, spawn_x, spawn_y, spawn_z, difficulty, game_type, is_forge, last_scanned_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(path) DO UPDATE SET
                    name=excluded.name,
                    seed=excluded.seed,
                    mc_version=excluded.mc_version,
                    spawn_x=excluded.spawn_x,
                    spawn_y=excluded.spawn_y,
                    spawn_z=excluded.spawn_z,
                    difficulty=excluded.difficulty,
                    game_type=excluded.game_type,
                    is_forge=excluded.is_forge,
                    last_scanned_at=CURRENT_TIMESTAMP
                """,
                (norm_path, name, str(seed) if seed is not None else None, mc_version, spawn_x, spawn_y, spawn_z, difficulty, game_type, 1 if is_forge else 0)
            )
            conn.commit()
            cursor.execute("SELECT id FROM worlds WHERE path = ?", (norm_path,))
            row = cursor.fetchone()
            return row["id"]

    def get_world_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        norm_path = os.path.abspath(path)
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM worlds WHERE path = ?", (norm_path,)).fetchone()
            return dict(row) if row else None

    def get_world_by_id(self, world_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM worlds WHERE id = ?", (world_id,)).fetchone()
            return dict(row) if row else None

    # --- Scanned Regions & Chunks (Caching) ---
    def is_region_scanned(self, world_id: int, dimension: str, region_file: str, mtime: float, size: int) -> bool:
        """Return True if this region file has already been scanned with the same mtime and size."""
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT mtime, size FROM scanned_regions
                WHERE world_id = ? AND dimension = ? AND region_file = ?
                """,
                (world_id, dimension, region_file)
            ).fetchone()
            if row and abs(row["mtime"] - mtime) < 0.001 and row["size"] == size:
                return True
            return False

    def get_scanned_chunk_updates(self, world_id: int, dimension: str) -> Dict[Tuple[int, int], Optional[int]]:
        """Return a mapping of (chunk_x, chunk_z) -> last_update for avoiding re-parsing unchanged chunks."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT chunk_x, chunk_z, last_update FROM chunks
                WHERE world_id = ? AND dimension = ?
                """,
                (world_id, dimension)
            ).fetchall()
            return {(r["chunk_x"], r["chunk_z"]): r["last_update"] for r in rows}

    def record_scanned_region(
        self,
        world_id: int,
        dimension: str,
        region_file: str,
        mtime: float,
        size: int,
        chunk_count: int
    ) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO scanned_regions (world_id, dimension, region_file, mtime, size, chunk_count, scanned_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(world_id, dimension, region_file) DO UPDATE SET
                    mtime=excluded.mtime,
                    size=excluded.size,
                    chunk_count=excluded.chunk_count,
                    scanned_at=CURRENT_TIMESTAMP
                """,
                (world_id, dimension, region_file, mtime, size, chunk_count)
            )
            conn.commit()

    def clear_region_data(self, world_id: int, dimension: str, min_cx: int, max_cx: int, min_cz: int, max_cz: int) -> None:
        """Clear existing entity data for a modified region before rescanning it."""
        with self.get_connection() as conn:
            params = (world_id, dimension, min_cx, max_cx, min_cz, max_cz)
            conn.execute(
                "DELETE FROM chunks WHERE world_id=? AND dimension=? AND chunk_x BETWEEN ? AND ? AND chunk_z BETWEEN ? AND ?",
                params
            )
            conn.execute(
                "DELETE FROM spawners WHERE world_id=? AND dimension=? AND chunk_x BETWEEN ? AND ? AND chunk_z BETWEEN ? AND ?",
                params
            )
            conn.execute(
                "DELETE FROM structures WHERE world_id=? AND dimension=? AND chunk_x BETWEEN ? AND ? AND chunk_z BETWEEN ? AND ?",
                params
            )
            conn.execute(
                "DELETE FROM chests WHERE world_id=? AND dimension=? AND chunk_x BETWEEN ? AND ? AND chunk_z BETWEEN ? AND ?",
                params
            )
            conn.execute(
                "DELETE FROM ore_veins WHERE world_id=? AND dimension=? AND chunk_x BETWEEN ? AND ? AND chunk_z BETWEEN ? AND ?",
                params
            )
            conn.commit()

    # --- Batch Insert Helpers ---
    def insert_chunks_batch(self, chunk_rows: List[Tuple]) -> None:
        """chunk_rows: [(world_id, dimension, chunk_x, chunk_z, last_update, dominant_biome_id, dominant_biome_name), ...]"""
        if not chunk_rows:
            return
        with self.get_connection() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO chunks
                (world_id, dimension, chunk_x, chunk_z, last_update, dominant_biome_id, dominant_biome_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                chunk_rows
            )
            conn.commit()

    def insert_spawners_batch(self, spawner_rows: List[Tuple]) -> None:
        """spawner_rows: [(world_id, dimension, entity_id, display_name, x, y, z, chunk_x, chunk_z, source, confidence), ...]"""
        if not spawner_rows:
            return
        with self.get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO spawners
                (world_id, dimension, entity_id, display_name, x, y, z, chunk_x, chunk_z, source, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                spawner_rows
            )
            conn.commit()

    def insert_structures_batch(self, struct_rows: List[Tuple]) -> None:
        """struct_rows: [(world_id, dimension, structure_id, name, min_x, max_x, min_y, max_y, min_z, max_z, center_x, center_y, center_z, chunk_x, chunk_z, source, confidence), ...]"""
        if not struct_rows:
            return
        with self.get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO structures
                (world_id, dimension, structure_id, name, min_x, max_x, min_y, max_y, min_z, max_z, center_x, center_y, center_z, chunk_x, chunk_z, source, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                struct_rows
            )
            conn.commit()

    def insert_chests_batch(self, chest_rows: List[Tuple]) -> None:
        """chest_rows: [(world_id, dimension, chest_type, x, y, z, chunk_x, chunk_z, loot_table, items_json, source, confidence), ...]"""
        if not chest_rows:
            return
        with self.get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO chests
                (world_id, dimension, chest_type, x, y, z, chunk_x, chunk_z, loot_table, items_json, source, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                chest_rows
            )
            conn.commit()

    def insert_ore_veins_batch(self, vein_rows: List[Tuple]) -> None:
        """vein_rows: [(world_id, dimension, ore_id, display_name, center_x, center_y, center_z, block_count, min_x, max_x, min_y, max_y, min_z, max_z, chunk_x, chunk_z), ...]"""
        if not vein_rows:
            return
        with self.get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO ore_veins
                (world_id, dimension, ore_id, display_name, center_x, center_y, center_z, block_count, min_x, max_x, min_y, max_y, min_z, max_z, chunk_x, chunk_z)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                vein_rows
            )
            conn.commit()

    def insert_mods_batch(self, world_id: int, mods: List[Dict[str, str]]) -> None:
        if not mods:
            return
        rows = [(world_id, m["id"], m.get("version", "")) for m in mods]
        with self.get_connection() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO mods (world_id, mod_id, version) VALUES (?, ?, ?)",
                rows
            )
            conn.commit()

    # --- Query API ---
    def get_world_stats(self, world_id: int) -> Dict[str, Any]:
        with self.get_connection() as conn:
            w = conn.execute("SELECT * FROM worlds WHERE id = ?", (world_id,)).fetchone()
            if not w:
                return {}

            dims = conn.execute("SELECT COUNT(DISTINCT dimension) as cnt FROM scanned_regions WHERE world_id = ?", (world_id,)).fetchone()["cnt"]
            regions = conn.execute("SELECT COUNT(*) as cnt FROM scanned_regions WHERE world_id = ?", (world_id,)).fetchone()["cnt"]
            chunks = conn.execute("SELECT COUNT(*) as cnt FROM chunks WHERE world_id = ?", (world_id,)).fetchone()["cnt"]
            spawners = conn.execute("SELECT COUNT(*) as cnt FROM spawners WHERE world_id = ?", (world_id,)).fetchone()["cnt"]
            structures = conn.execute("SELECT COUNT(*) as cnt FROM structures WHERE world_id = ?", (world_id,)).fetchone()["cnt"]
            chests = conn.execute("SELECT COUNT(*) as cnt FROM chests WHERE world_id = ?", (world_id,)).fetchone()["cnt"]
            veins = conn.execute("SELECT COUNT(*) as cnt, COALESCE(SUM(block_count), 0) as blocks FROM ore_veins WHERE world_id = ?", (world_id,)).fetchone()
            biomes = conn.execute("SELECT COUNT(DISTINCT dominant_biome_id) as cnt FROM chunks WHERE world_id = ?", (world_id,)).fetchone()["cnt"]

            return {
                "world_name": w["name"],
                "seed": w["seed"],
                "mc_version": w["mc_version"],
                "spawn": {"x": w["spawn_x"], "y": w["spawn_y"], "z": w["spawn_z"]},
                "difficulty": w["difficulty"],
                "game_type": w["game_type"],
                "is_forge": bool(w["is_forge"]),
                "dimensions_count": dims,
                "regions_count": regions,
                "chunks_count": chunks,
                "structures_count": structures,
                "spawners_count": spawners,
                "chests_count": chests,
                "ore_veins_count": veins["cnt"],
                "ore_blocks_count": veins["blocks"],
                "biome_types_count": biomes
            }

    def get_ore_breakdown(self, world_id: int, dimension: str) -> List[Dict[str, Any]]:
        """Distinct ore types with their vein count and total block count,
        for the current dimension, richest first."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT ore_id, display_name, COUNT(*) AS vein_count, SUM(block_count) AS block_count
                FROM ore_veins
                WHERE world_id = ? AND dimension = ?
                GROUP BY ore_id
                ORDER BY block_count DESC
                """,
                (world_id, dimension)
            ).fetchall()
            return [
                {
                    "ore_id": r["ore_id"],
                    "display_name": r["display_name"],
                    "vein_count": r["vein_count"],
                    "block_count": r["block_count"]
                }
                for r in rows
            ]

    def get_markers(
        self,
        world_id: int,
        dimension: str,
        min_x: Optional[int] = None,
        max_x: Optional[int] = None,
        min_z: Optional[int] = None,
        max_z: Optional[int] = None,
        include_ores: bool = True,
        include_spawners: bool = True,
        include_structures: bool = True,
        include_chests: bool = True,
        ore_filter: Optional[List[str]] = None,
        spawner_filter: Optional[List[str]] = None,
        structure_filter: Optional[List[str]] = None,
        limit: int = 2000
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        with self.get_connection() as conn:
            # 1. Spawners
            if include_spawners:
                query = "SELECT * FROM spawners WHERE world_id = ? AND dimension = ?"
                params: List[Any] = [world_id, dimension]
                if min_x is not None:
                    query += " AND x BETWEEN ? AND ? AND z BETWEEN ? AND ?"
                    params.extend([min_x, max_x, min_z, max_z])
                if spawner_filter:
                    placeholders = ",".join("?" * len(spawner_filter))
                    query += f" AND entity_id IN ({placeholders})"
                    params.extend(spawner_filter)
                query += f" LIMIT {limit}"
                for r in conn.execute(query, params):
                    results.append({
                        "id": f"spawner_{r['id']}",
                        "category": "spawner",
                        "type": r["entity_id"],
                        "name": r["display_name"],
                        "x": r["x"],
                        "y": r["y"],
                        "z": r["z"],
                        "source": r["source"],
                        "confidence": r["confidence"]
                    })

            # 2. Structures
            if include_structures:
                query = "SELECT * FROM structures WHERE world_id = ? AND dimension = ?"
                params = [world_id, dimension]
                if min_x is not None:
                    query += " AND center_x BETWEEN ? AND ? AND center_z BETWEEN ? AND ?"
                    params.extend([min_x, max_x, min_z, max_z])
                if structure_filter:
                    placeholders = ",".join("?" * len(structure_filter))
                    query += f" AND structure_id IN ({placeholders})"
                    params.extend(structure_filter)
                query += f" LIMIT {limit}"
                for r in conn.execute(query, params):
                    results.append({
                        "id": f"structure_{r['id']}",
                        "category": "structure",
                        "type": r["structure_id"],
                        "name": r["name"],
                        "x": r["center_x"],
                        "y": r["center_y"],
                        "z": r["center_z"],
                        "bbox": [r["min_x"], r["min_y"], r["min_z"], r["max_x"], r["max_y"], r["max_z"]],
                        "source": r["source"],
                        "confidence": r["confidence"]
                    })

            # 3. Chests
            if include_chests:
                query = "SELECT * FROM chests WHERE world_id = ? AND dimension = ?"
                params = [world_id, dimension]
                if min_x is not None:
                    query += " AND x BETWEEN ? AND ? AND z BETWEEN ? AND ?"
                    params.extend([min_x, max_x, min_z, max_z])
                query += f" LIMIT {limit}"
                for r in conn.execute(query, params):
                    items = json.loads(r["items_json"]) if r["items_json"] else []
                    results.append({
                        "id": f"chest_{r['id']}",
                        "category": "chest",
                        "type": r["chest_type"],
                        "name": "Chest" if "chest" in r["chest_type"] else "Container",
                        "x": r["x"],
                        "y": r["y"],
                        "z": r["z"],
                        "loot_table": r["loot_table"],
                        "items": items,
                        "source": r["source"],
                        "confidence": r["confidence"]
                    })

            # 4. Ore Veins
            # This table can be enormous (a heavily-modded world can log
            # a row per isolated ore block — millions of rows). Individual
            # veins render fine once zoomed in, but a wide zoomed-out view
            # can still contain far more veins than the LIMIT allows, so
            # rendering an arbitrary subset both looks incomplete and does
            # no favors for perf. Past an area threshold, collapse the
            # view into density clusters instead: one square per grid
            # cell with a combined block/vein count, cheap to compute
            # (one GROUP BY over the indexed bbox range) and cheap to
            # render (far fewer shapes than raw rows).
            if include_ores:
                area = None
                if min_x is not None:
                    area = (max_x - min_x) * (max_z - min_z)

                grid_size = None
                if area is not None:
                    if area > 20_000_000:
                        grid_size = 256
                    elif area > 6_000_000:
                        grid_size = 128

                if grid_size:
                    query = """
                        SELECT
                            CAST(center_x / ? AS INT) AS gx,
                            CAST(center_z / ? AS INT) AS gz,
                            SUM(block_count) AS total_blocks,
                            COUNT(*) AS vein_count
                        FROM ore_veins
                        WHERE world_id = ? AND dimension = ?
                          AND center_x BETWEEN ? AND ? AND center_z BETWEEN ? AND ?
                    """
                    params: List[Any] = [grid_size, grid_size, world_id, dimension, min_x, max_x, min_z, max_z]
                    if ore_filter:
                        placeholders = ",".join("?" * len(ore_filter))
                        query += f" AND ore_id IN ({placeholders})"
                        params.extend(ore_filter)
                    query += " GROUP BY gx, gz LIMIT ?"
                    params.append(limit)

                    for r in conn.execute(query, params):
                        cx = r["gx"] * grid_size + grid_size // 2
                        cz = r["gz"] * grid_size + grid_size // 2
                        results.append({
                            "id": f"orecluster_{r['gx']}_{r['gz']}",
                            "category": "ore_cluster",
                            "name": f"{r['vein_count']} ore veins",
                            "x": cx,
                            "y": 64,
                            "z": cz,
                            "blocks": r["total_blocks"],
                            "vein_count": r["vein_count"],
                            "bbox": [cx - grid_size // 2, 0, cz - grid_size // 2, cx + grid_size // 2, 255, cz + grid_size // 2],
                            "source": "Aggregated (zoomed out)",
                            "confidence": "HIGH"
                        })
                else:
                    query = "SELECT * FROM ore_veins WHERE world_id = ? AND dimension = ?"
                    params = [world_id, dimension]
                    if min_x is not None:
                        query += " AND center_x BETWEEN ? AND ? AND center_z BETWEEN ? AND ?"
                        params.extend([min_x, max_x, min_z, max_z])
                    if ore_filter:
                        placeholders = ",".join("?" * len(ore_filter))
                        query += f" AND ore_id IN ({placeholders})"
                        params.extend(ore_filter)
                    query += f" LIMIT {limit}"
                    for r in conn.execute(query, params):
                        results.append({
                            "id": f"vein_{r['id']}",
                            "category": "ore",
                            "type": r["ore_id"],
                            "name": r["display_name"],
                            "x": r["center_x"],
                            "y": r["center_y"],
                            "z": r["center_z"],
                            "blocks": r["block_count"],
                            "bbox": [r["min_x"], r["min_y"], r["min_z"], r["max_x"], r["max_y"], r["max_z"]],
                            "source": "Generated Chunk NBT",
                            "confidence": "HIGH"
                        })

        return results

    def get_chunk_biomes(
        self,
        world_id: int,
        dimension: str,
        min_chunk_x: Optional[int] = None,
        max_chunk_x: Optional[int] = None,
        min_chunk_z: Optional[int] = None,
        max_chunk_z: Optional[int] = None,
        limit: int = 6000
    ) -> List[Dict[str, Any]]:
        query = """
            SELECT chunk_x, chunk_z, dominant_biome_id, dominant_biome_name
            FROM chunks WHERE world_id = ? AND dimension = ?
        """
        params: List[Any] = [world_id, dimension]
        if min_chunk_x is not None:
            query += " AND chunk_x BETWEEN ? AND ? AND chunk_z BETWEEN ? AND ?"
            params.extend([min_chunk_x, max_chunk_x, min_chunk_z, max_chunk_z])
        query += " LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def search_features(
        self,
        world_id: int,
        dimension: str,
        query: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        q = f"%{query.strip()}%"

        with self.get_connection() as conn:
            # Search spawners
            for r in conn.execute(
                """
                SELECT * FROM spawners
                WHERE world_id = ? AND dimension = ? AND (entity_id LIKE ? OR display_name LIKE ?)
                LIMIT ?
                """,
                (world_id, dimension, q, q, limit)
            ):
                results.append({
                    "category": "spawner",
                    "name": r["display_name"],
                    "dimension": r["dimension"],
                    "x": r["x"],
                    "y": r["y"],
                    "z": r["z"],
                    "source": r["source"],
                    "confidence": r["confidence"]
                })

            # Search structures
            for r in conn.execute(
                """
                SELECT * FROM structures
                WHERE world_id = ? AND dimension = ? AND (structure_id LIKE ? OR name LIKE ?)
                LIMIT ?
                """,
                (world_id, dimension, q, q, limit)
            ):
                results.append({
                    "category": "structure",
                    "name": r["name"],
                    "dimension": r["dimension"],
                    "x": r["center_x"],
                    "y": r["center_y"],
                    "z": r["center_z"],
                    "source": r["source"],
                    "confidence": r["confidence"]
                })

            # Search ore veins
            for r in conn.execute(
                """
                SELECT * FROM ore_veins
                WHERE world_id = ? AND dimension = ? AND (ore_id LIKE ? OR display_name LIKE ?)
                LIMIT ?
                """,
                (world_id, dimension, q, q, limit)
            ):
                results.append({
                    "category": "ore",
                    "name": f"{r['display_name']} ({r['block_count']} blocks)",
                    "dimension": r["dimension"],
                    "x": r["center_x"],
                    "y": r["center_y"],
                    "z": r["center_z"],
                    "source": "Generated Chunk NBT",
                    "confidence": "HIGH"
                })

            # Search biomes
            for r in conn.execute(
                """
                SELECT DISTINCT dominant_biome_id, dominant_biome_name, chunk_x, chunk_z FROM chunks
                WHERE world_id = ? AND dimension = ? AND (dominant_biome_id LIKE ? OR dominant_biome_name LIKE ?)
                LIMIT ?
                """,
                (world_id, dimension, q, q, limit)
            ):
                results.append({
                    "category": "biome",
                    "name": r["dominant_biome_name"],
                    "dimension": dimension,
                    "x": r["chunk_x"] * 16 + 8,
                    "y": 64,
                    "z": r["chunk_z"] * 16 + 8,
                    "source": "Generated Chunk NBT",
                    "confidence": "HIGH"
                })

        return results[:limit]

    def find_nearest(
        self,
        world_id: int,
        dimension: str,
        feature_type: str,
        subtype: Optional[str],
        current_x: int,
        current_y: int,
        current_z: int,
        max_distance: int = 50000
    ) -> Optional[Dict[str, Any]]:
        """Find the nearest feature to (current_x, current_z) using Euclidean distance in SQLite."""
        max_dist_sq = max_distance * max_distance

        with self.get_connection() as conn:
            if feature_type == "ore":
                query = """
                    SELECT *,
                    ((center_x - ?) * (center_x - ?) + (center_z - ?) * (center_z - ?)) AS dist_sq
                    FROM ore_veins
                    WHERE world_id = ? AND dimension = ?
                """
                params = [current_x, current_x, current_z, current_z, world_id, dimension]
                if subtype:
                    query += " AND ore_id LIKE ?"
                    params.append(f"%{subtype}%")
                query += " AND dist_sq <= ? ORDER BY dist_sq ASC LIMIT 1"
                params.append(max_dist_sq)

                row = conn.execute(query, params).fetchone()
                if row:
                    dist = int((row["dist_sq"]) ** 0.5)
                    return {
                        "category": "ore",
                        "name": f"{row['display_name']} ({row['block_count']} blocks)",
                        "x": row["center_x"],
                        "y": row["center_y"],
                        "z": row["center_z"],
                        "distance": dist,
                        "source": "Generated Chunk NBT",
                        "confidence": "HIGH"
                    }

            elif feature_type == "spawner":
                query = """
                    SELECT *,
                    ((x - ?) * (x - ?) + (z - ?) * (z - ?)) AS dist_sq
                    FROM spawners
                    WHERE world_id = ? AND dimension = ?
                """
                params = [current_x, current_x, current_z, current_z, world_id, dimension]
                if subtype:
                    query += " AND entity_id LIKE ?"
                    params.append(f"%{subtype}%")
                query += " AND dist_sq <= ? ORDER BY dist_sq ASC LIMIT 1"
                params.append(max_dist_sq)

                row = conn.execute(query, params).fetchone()
                if row:
                    dist = int((row["dist_sq"]) ** 0.5)
                    return {
                        "category": "spawner",
                        "name": row["display_name"],
                        "x": row["x"],
                        "y": row["y"],
                        "z": row["z"],
                        "distance": dist,
                        "source": row["source"],
                        "confidence": row["confidence"]
                    }

            elif feature_type == "structure":
                query = """
                    SELECT *,
                    ((center_x - ?) * (center_x - ?) + (center_z - ?) * (center_z - ?)) AS dist_sq
                    FROM structures
                    WHERE world_id = ? AND dimension = ?
                """
                params = [current_x, current_x, current_z, current_z, world_id, dimension]
                if subtype:
                    query += " AND (structure_id LIKE ? OR name LIKE ?)"
                    params.extend([f"%{subtype}%", f"%{subtype}%"])
                query += " AND dist_sq <= ? ORDER BY dist_sq ASC LIMIT 1"
                params.append(max_dist_sq)

                row = conn.execute(query, params).fetchone()
                if row:
                    dist = int((row["dist_sq"]) ** 0.5)
                    return {
                        "category": "structure",
                        "name": row["name"],
                        "x": row["center_x"],
                        "y": row["center_y"],
                        "z": row["center_z"],
                        "distance": dist,
                        "source": row["source"],
                        "confidence": row["confidence"]
                    }

            elif feature_type == "biome":
                # Find nearest chunk with matching biome
                query = """
                    SELECT *,
                    (((chunk_x * 16 + 8) - ?) * ((chunk_x * 16 + 8) - ?) + ((chunk_z * 16 + 8) - ?) * ((chunk_z * 16 + 8) - ?)) AS dist_sq
                    FROM chunks
                    WHERE world_id = ? AND dimension = ?
                """
                params = [current_x, current_x, current_z, current_z, world_id, dimension]
                if subtype:
                    query += " AND (dominant_biome_id LIKE ? OR dominant_biome_name LIKE ?)"
                    params.extend([f"%{subtype}%", f"%{subtype}%"])
                query += " AND dist_sq <= ? ORDER BY dist_sq ASC LIMIT 1"
                params.append(max_dist_sq)

                row = conn.execute(query, params).fetchone()
                if row:
                    dist = int((row["dist_sq"]) ** 0.5)
                    return {
                        "category": "biome",
                        "name": row["dominant_biome_name"],
                        "x": row["chunk_x"] * 16 + 8,
                        "y": 64,
                        "z": row["chunk_z"] * 16 + 8,
                        "distance": dist,
                        "source": "Generated Chunk NBT",
                        "confidence": "HIGH"
                    }

        return None

    def export_all_json(self, world_id: int, out_path: str) -> None:
        """Export the entire indexed world to a single JSON file for easy Git tracking."""
        data = {
            "stats": self.get_world_stats(world_id),
            "spawners": self.get_markers(world_id, "minecraft:overworld", include_ores=False, include_structures=False, include_chests=False, limit=10000),
            "structures": self.get_markers(world_id, "minecraft:overworld", include_ores=False, include_spawners=False, include_chests=False, limit=10000),
            "chests": self.get_markers(world_id, "minecraft:overworld", include_ores=False, include_spawners=False, include_structures=False, limit=10000),
            "ore_veins": self.get_markers(world_id, "minecraft:overworld", include_structures=False, include_spawners=False, include_chests=False, limit=10000)
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

db = Database()
