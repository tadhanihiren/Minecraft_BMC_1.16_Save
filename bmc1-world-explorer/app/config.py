from pathlib import Path
import os

# Project root: bmc1-world-explorer
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Single-file SQLite database
DATABASE_PATH = DATA_DIR / "world_explorer.db"

# Default world path (the parent directory if it contains level.dat)
PARENT_DIR = PROJECT_ROOT.parent
if (PARENT_DIR / "level.dat").exists():
    DEFAULT_WORLD_PATH = str(PARENT_DIR.resolve())
else:
    DEFAULT_WORLD_PATH = ""

HOST = "127.0.0.1"
PORT = 8000
