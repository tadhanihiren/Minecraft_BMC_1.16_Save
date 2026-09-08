import gzip
import os
import logging
from typing import Dict, Any, List, Optional
from app.scanner.nbt_reader import parse_nbt

logger = logging.getLogger(__name__)

GAME_TYPE_NAMES = {
    0: "Survival",
    1: "Creative",
    2: "Adventure",
    3: "Spectator"
}

DIFFICULTY_NAMES = {
    0: "Peaceful",
    1: "Easy",
    2: "Normal",
    3: "Hard"
}

class LevelData:
    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.data = raw.get("Data", {})
        self.fml = raw.get("fml", {})

    @property
    def world_name(self) -> str:
        return self.data.get("LevelName", "Unknown World")

    @property
    def seed(self) -> Optional[int]:
        wgs = self.data.get("WorldGenSettings")
        if isinstance(wgs, dict) and "seed" in wgs:
            return wgs["seed"]
        return self.data.get("RandomSeed")

    @property
    def mc_version(self) -> str:
        ver = self.data.get("Version")
        if isinstance(ver, dict):
            return ver.get("Name", "1.16.5")
        return "1.16.5"

    @property
    def mc_version_id(self) -> int:
        ver = self.data.get("Version")
        if isinstance(ver, dict):
            return ver.get("Id", 2586)
        return 2586

    @property
    def spawn_coords(self) -> Dict[str, int]:
        return {
            "x": self.data.get("SpawnX", 0),
            "y": self.data.get("SpawnY", 64),
            "z": self.data.get("SpawnZ", 0)
        }

    @property
    def game_type(self) -> str:
        gt = self.data.get("GameType", 0)
        return GAME_TYPE_NAMES.get(gt, f"Unknown ({gt})")

    @property
    def difficulty(self) -> str:
        diff = self.data.get("Difficulty", 2)
        return DIFFICULTY_NAMES.get(diff, f"Unknown ({diff})")

    @property
    def is_forge(self) -> bool:
        return bool(self.fml or "forge" in self.raw)

    def get_installed_mods(self) -> List[Dict[str, str]]:
        """Return list of {mod_id, version} from FML LoadingModList."""
        mod_list = self.fml.get("LoadingModList", [])
        mods = []
        for m in mod_list:
            if isinstance(m, dict):
                mods.append({
                    "id": m.get("ModId", "unknown"),
                    "version": m.get("ModVersion", "unknown")
                })
        return mods

    def get_biome_registry(self) -> Dict[int, str]:
        """
        Return mapping from integer biome ID to canonical string ID
        (e.g., 150 -> 'byg:jacaranda_forest').
        """
        registries = self.fml.get("Registries", {})
        biome_reg = registries.get("minecraft:worldgen/biome", {})
        id_map: Dict[int, str] = {}
        if isinstance(biome_reg, dict):
            ids_list = biome_reg.get("ids", [])
            for item in ids_list:
                if isinstance(item, dict) and "V" in item and "K" in item:
                    id_map[int(item["V"])] = str(item["K"])
        return id_map

    def get_worldgen_dimensions(self) -> List[str]:
        """Return dimensions configured in WorldGenSettings."""
        wgs = self.data.get("WorldGenSettings")
        if isinstance(wgs, dict) and "dimensions" in wgs:
            return list(wgs["dimensions"].keys())
        return ["minecraft:overworld", "minecraft:the_nether", "minecraft:the_end"]

def read_level_dat(world_folder: str) -> LevelData:
    """Read level.dat safely from a world directory in read-only mode."""
    level_dat_path = os.path.join(world_folder, "level.dat")
    if not os.path.exists(level_dat_path):
        raise FileNotFoundError(f"level.dat not found in {world_folder}")

    with gzip.open(level_dat_path, "rb") as f:
        data = f.read()

    _, root = parse_nbt(data)
    return LevelData(root)
