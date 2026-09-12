import os
import time
import json
import logging
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field

from app.scanner.level_parser import read_level_dat
from app.scanner.dimensions import discover_dimensions, DimensionInfo
from app.scanner.mca_reader import MCAReader, parse_region_coords
from app.scanner.block_states import find_ores_in_section
from app.scanner.ores import cluster_ore_veins
from app.scanner.spawners import extract_spawner
from app.scanner.chests import extract_chest
from app.scanner.structures import extract_structures_from_chunk
from app.scanner.biomes import extract_chunk_biomes
from app.database.database import db

logger = logging.getLogger(__name__)

@dataclass
class ScanProgress:
    is_scanning: bool = False
    is_completed: bool = False
    cancelled: bool = False
    current_world_name: str = ""
    current_dimension: str = ""
    total_regions: int = 0
    scanned_regions: int = 0
    total_chunks: int = 0
    total_spawners: int = 0
    total_structures: int = 0
    total_chests: int = 0
    total_ore_veins: int = 0
    total_ore_blocks: int = 0
    percentage: float = 0.0
    status_message: str = "Idle"
    errors: List[str] = field(default_factory=list)

class WorldScanner:
    def __init__(self):
        self.progress = ScanProgress()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def get_progress(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "is_scanning": self.progress.is_scanning,
                "is_completed": self.progress.is_completed,
                "cancelled": self.progress.cancelled,
                "world_name": self.progress.current_world_name,
                "dimension": self.progress.current_dimension,
                "total_regions": self.progress.total_regions,
                "scanned_regions": self.progress.scanned_regions,
                "total_chunks": self.progress.total_chunks,
                "total_spawners": self.progress.total_spawners,
                "total_structures": self.progress.total_structures,
                "total_chests": self.progress.total_chests,
                "total_ore_veins": self.progress.total_ore_veins,
                "total_ore_blocks": self.progress.total_ore_blocks,
                "percentage": round(self.progress.percentage, 1),
                "status_message": self.progress.status_message,
                "errors_count": len(self.progress.errors),
                "recent_errors": self.progress.errors[-5:]
            }

    def cancel_scan(self) -> None:
        with self._lock:
            if self.progress.is_scanning:
                self.progress.cancelled = True
                self.progress.status_message = "Cancelling scan..."

    def start_scan(self, world_folder: str, force_rescan: bool = False, dimension_id: Optional[str] = None) -> bool:
        with self._lock:
            if self.progress.is_scanning:
                return False
            self.progress = ScanProgress(
                is_scanning=True,
                status_message="Initializing world scan..."
            )

        self._thread = threading.Thread(
            target=self._run_scan,
            args=(world_folder, force_rescan, dimension_id),
            daemon=True
        )
        self._thread.start()
        return True

    def _run_scan(self, world_folder: str, force_rescan: bool, target_dim_id: Optional[str]) -> None:
        try:
            logger.info(f"Starting world scan on: {world_folder}")
            # 1. Read level.dat
            level_data = read_level_dat(world_folder)
            spawn = level_data.spawn_coords

            world_id = db.upsert_world(
                path=world_folder,
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

            # Biome registry
            biome_registry = level_data.get_biome_registry()

            with self._lock:
                self.progress.current_world_name = level_data.world_name

            # 2. Discover dimensions
            all_dimensions = discover_dimensions(world_folder)
            if target_dim_id:
                dimensions = [d for d in all_dimensions if d.id == target_dim_id]
            else:
                dimensions = all_dimensions

            # Count total regions across selected dimensions
            total_mca_files = 0
            dimension_files: Dict[str, List[str]] = {}
            for dim in dimensions:
                files = []
                if os.path.exists(dim.region_dir):
                    for fname in os.listdir(dim.region_dir):
                        if fname.endswith(".mca"):
                            files.append(os.path.join(dim.region_dir, fname))
                dimension_files[dim.id] = files
                total_mca_files += len(files)

            with self._lock:
                self.progress.total_regions = total_mca_files
                self.progress.status_message = f"Found {total_mca_files} region files across {len(dimensions)} dimensions"

            scanned_region_count = 0

            # 3. Process each dimension
            for dim in dimensions:
                if self.progress.cancelled:
                    break

                with self._lock:
                    self.progress.current_dimension = dim.name

                mca_files = dimension_files.get(dim.id, [])
                known_chunk_updates = db.get_scanned_chunk_updates(world_id, dim.id)

                for mca_path in mca_files:
                    if self.progress.cancelled:
                        break

                    fname = os.path.basename(mca_path)
                    try:
                        mtime = os.path.getmtime(mca_path)
                        size = os.path.getsize(mca_path)

                        # Check level 1 cache: Unchanged region file?
                        if not force_rescan and db.is_region_scanned(world_id, dim.id, fname, mtime, size):
                            scanned_region_count += 1
                            with self._lock:
                                self.progress.scanned_regions = scanned_region_count
                                self.progress.percentage = (scanned_region_count / max(1, total_mca_files)) * 100.0
                            continue

                        with self._lock:
                            self.progress.status_message = f"Scanning {dim.name}: {fname}"

                        coords = parse_region_coords(fname)
                        if not coords:
                            continue
                        rx, rz = coords

                        # Clear old data for this region in case of rescan
                        min_cx, max_cx = rx * 32, rx * 32 + 31
                        min_cz, max_cz = rz * 32, rz * 32 + 31
                        db.clear_region_data(world_id, dim.id, min_cx, max_cx, min_cz, max_cz)

                        reader = MCAReader(mca_path)
                        region_chunks = 0

                        chunk_batch = []
                        spawner_batch = []
                        chest_batch = []
                        struct_batch = []
                        region_ore_blocks = []

                        for cx, cz, chunk_nbt in reader.read_chunks():
                            if self.progress.cancelled:
                                break

                            level = chunk_nbt.get("Level", {})
                            last_update = level.get("LastUpdate")
                            region_chunks += 1

                            # Check level 2 cache: Unchanged chunk?
                            if not force_rescan and (cx, cz) in known_chunk_updates:
                                if known_chunk_updates[(cx, cz)] == last_update:
                                    continue

                            # Extract Biome
                            biome_id, biome_name = extract_chunk_biomes(chunk_nbt, biome_registry)
                            chunk_batch.append((
                                world_id, dim.id, cx, cz, last_update, biome_id, biome_name
                            ))

                            # Extract Spawners & Chests from TileEntities
                            tile_entities = level.get("TileEntities", [])
                            for te in tile_entities:
                                if not isinstance(te, dict):
                                    continue

                                # Spawner
                                spawner = extract_spawner(te)
                                if spawner:
                                    spawner_batch.append((
                                        world_id, dim.id, spawner.entity_id, spawner.display_name,
                                        spawner.x, spawner.y, spawner.z, cx, cz,
                                        spawner.source, spawner.confidence
                                    ))

                                # Chest / Container
                                chest = extract_chest(te)
                                if chest:
                                    items_json = json.dumps([
                                        {"id": it.id, "count": it.count, "slot": it.slot}
                                        for it in chest.items
                                    ]) if chest.items else None
                                    chest_batch.append((
                                        world_id, dim.id, chest.chest_type,
                                        chest.x, chest.y, chest.z, cx, cz,
                                        chest.loot_table, items_json,
                                        chest.source, chest.confidence
                                    ))

                            # Extract Confirmed Structures
                            structures = extract_structures_from_chunk(chunk_nbt, cx, cz)
                            for st in structures:
                                struct_batch.append((
                                    world_id, dim.id, st.structure_id, st.name,
                                    st.min_x, st.max_x, st.min_y, st.max_y, st.min_z, st.max_z,
                                    st.center_x, st.center_y, st.center_z,
                                    cx, cz, st.source, st.confidence
                                ))

                            # Extract Ore Blocks from Sections
                            sections = level.get("Sections", [])
                            for sec in sections:
                                if isinstance(sec, dict):
                                    sy = sec.get("Y", 0)
                                    ores = find_ores_in_section(sec, cx, cz, sy)
                                    if ores:
                                        region_ore_blocks.extend(ores)

                        # Cluster ores in this region into veins
                        ore_veins = cluster_ore_veins(region_ore_blocks)
                        vein_batch = []
                        total_ore_blocks_in_veins = 0
                        for v in ore_veins:
                            vein_batch.append((
                                world_id, dim.id, v.ore_id,
                                v.ore_id.split(":")[-1].replace("_", " ").title(),
                                v.center_x, v.center_y, v.center_z,
                                v.block_count,
                                v.min_x, v.max_x, v.min_y, v.max_y, v.min_z, v.max_z,
                                v.center_x >> 4, v.center_z >> 4
                            ))
                            total_ore_blocks_in_veins += v.block_count

                        # Batch save to SQLite
                        db.insert_chunks_batch(chunk_batch)
                        db.insert_spawners_batch(spawner_batch)
                        db.insert_structures_batch(struct_batch)
                        db.insert_chests_batch(chest_batch)
                        db.insert_ore_veins_batch(vein_batch)

                        # Record region as scanned (Caching)
                        db.record_scanned_region(world_id, dim.id, fname, mtime, size, region_chunks)

                        scanned_region_count += 1
                        with self._lock:
                            self.progress.scanned_regions = scanned_region_count
                            self.progress.total_chunks += region_chunks
                            self.progress.total_spawners += len(spawner_batch)
                            self.progress.total_structures += len(struct_batch)
                            self.progress.total_chests += len(chest_batch)
                            self.progress.total_ore_veins += len(vein_batch)
                            self.progress.total_ore_blocks += total_ore_blocks_in_veins
                            self.progress.percentage = (scanned_region_count / max(1, total_mca_files)) * 100.0

                    except Exception as e:
                        err_msg = f"Error scanning region {fname}: {e}"
                        logger.warning(err_msg)
                        with self._lock:
                            self.progress.errors.append(err_msg)

            # Flush WAL into main single .db file so Git tracking is immediate
            db.checkpoint()

            with self._lock:
                self.progress.is_scanning = False
                self.progress.is_completed = True
                self.progress.percentage = 100.0
                if self.progress.cancelled:
                    self.progress.status_message = "Scan was cancelled."
                else:
                    self.progress.status_message = "World scan completed successfully!"

            logger.info("World scan finished.")

        except Exception as e:
            logger.error(f"Scan failed with error: {e}", exc_info=True)
            with self._lock:
                self.progress.is_scanning = False
                self.progress.status_message = f"Scan failed: {e}"
                self.progress.errors.append(str(e))

scanner = WorldScanner()
