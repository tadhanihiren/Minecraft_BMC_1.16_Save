# BMC1 World Explorer

A dedicated, offline, read-only Windows application for analyzing and visualizing **Better MC [FORGE] BMC1 v62 (Minecraft 1.16.5)** worlds.

---

## 🌟 Features

- **Strictly Read-Only & Safe**: Never modifies your Minecraft world files. Opens `.mca` and `level.dat` files in binary read-only mode (`rb`).
- **Targeted Minecraft Java 1.16.5 Anvil / NBT Reader**: Custom high-performance pure-Python NBT and Anvil `.mca` reader built strictly for 1.16.5 format (handles section bit-unpacking, negative coordinates without truncation, and corrupt chunk recovery).
- **Two-Level Smart Caching**:
  - **Level 1 (Region cache)**: Skips unchanged `.mca` files based on timestamp and file size in 0ms.
  - **Level 2 (Chunk cache)**: Only scans modified or newly generated chunks based on `LastUpdate` timestamps. Never re-checks already-checked chunks!
- **Single-File Database & Git Compatible**:
  - All data is indexed into a single self-contained SQLite file: `data/world_explorer.db`.
  - Automatic WAL checkpointing flushes all changes into the single file.
  - One-click **"Save for Git"** creates a lightweight, text-based `data/world_data.json` (~6 MB) that can be committed directly to GitHub without hitting file size limits.
- **Interactive Offline Map**:
  - Built with Leaflet.js with bundled assets (100% offline, zero internet connection required).
  - True Minecraft Coordinate Reference System: X increases East, Z increases South (North is negative Z).
  - Live coordinates HUD on mouse hover with Block (X, Z), Chunk (X, Z), and Region file name.
  - Visual overlays for Ores, Spawners, Structures, Chests, and Biome regions.
- **Entity & Resource Detection**:
  - **Mob Spawners**: Exact coordinates, entity IDs (Zombie, Skeleton, Spider, Cave Spider, etc.), confidence HIGH.
  - **Ore Veins**: Scans vanilla and BMC1 modded ores (`cavesandcliffs`, `darkerdepths`). Automatically clusters adjacent blocks into coherent veins with center coordinates and bounding boxes.
  - **Confirmed Structures**: Detects structure starts and bounding boxes directly from generated chunk data (Villages, Mineshafts, Strongholds, Dungeons Plus, Repurposed Structures, YUNG's Better Dungeons, etc.).
  - **Chests & Containers**: Exact coordinates, loot table IDs, and generated inventory items.
  - **Biomes**: Reads 1024-int biome arrays and resolves names through Forge's FML registry (over 396+ BMC1 biomes supported).
- **Global & Nearest Search**:
  - Search by name, block type, or direct coordinates (`X, Y, Z`).
  - "Find Nearest" calculation: Quickly find the nearest Diamond vein, Zombie spawner, Village, or Biome from your current player coordinates.
- **Copy Commands**: Click any location or marker to copy raw coordinates (`X Y Z`) or the in-game command `/tp @s X Y Z`.
- **Export**: Export any category or all features to CSV or JSON.

---

## 📋 System Requirements

- **OS**: Windows 10 or Windows 11
- **Python**: Python 3.12 or 3.13 (Python 3.13 tested and verified)
- **Target Minecraft Version**: Minecraft Java Edition 1.16.5 (Forge / BMC1 v62)

---

## 🚀 Quick Start

### 1. Double-Click Launch (Windows)

Simply double-click `run.bat` in this folder:

```text
run.bat
```

The script will automatically:
1. Detect Python
2. Set up the virtual environment (`.venv`)
3. Install dependencies from `requirements.txt`
4. Start the FastAPI server on `http://127.0.0.1:8000`
5. Automatically open your default browser to the application

### 2. Manual Command Line

```cmd
cd f:\Saves\golida\bmc1-world-explorer
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

Then open `http://127.0.0.1:8000` in your web browser.

---

## 🗺️ How to Use

### 1. World Selection
By default, the application automatically detects and loads the parent world folder (`F:\Saves\golida`).
To analyze a different world, click **"📁 Open World"** in the top navigation bar and enter the path.

### 2. Scanning
- Click **"⚡ Scan World"**: Performs an incremental scan. It checks which regions and chunks have already been indexed in `data/world_explorer.db` and skips them instantly. Only newly generated chunks are scanned.
- Click **"🔄 Force Rescan"**: Clears and rescans the entire selected dimension from scratch.
- Live progress is shown in the top status bar (progress percentage, chunk count, spawner count, ore count).

### 3. Map Controls & Navigation
- **Pan & Zoom**: Click and drag to pan; use scroll wheel or `+`/`-` buttons to zoom.
- **Coordinates HUD**: Hovering over the map shows real-time Minecraft Block coordinates, Chunk coordinates, and the exact `.mca` region filename.
- **Inspect**: Click any point or marker to inspect details in the bottom card.
- **Teleport**: Click **"⚡ Copy /tp"** to copy `/tp @s X Y Z` directly into your clipboard, then paste into Minecraft chat.

### 4. Filters & Sub-filters
- In the **Filters** sidebar tab, toggle master categories:
  - 🌳 Biome Overlays
  - 💎 Ore Veins
  - 🧟 Mob Spawners
  - 🏰 Structures
  - 🎁 Chests
- Expand specific sub-categories to isolate particular ores (e.g. Diamond only) or specific spawner types (e.g. Skeleton only).

### 5. Find Nearest
1. Click the **"Find Nearest"** tab in the sidebar.
2. Select the feature type (Ore Vein, Mob Spawner, Structure, Biome).
3. Optionally specify a subtype (e.g., `diamond`, `zombie`, `village`).
4. Enter your current player coordinates (X, Y, Z).
5. Click **"🔍 Find Nearest"**. The closest match is computed using Euclidean distance and you can click **"Jump to Location"** to center the map on it.

### 6. Locations Table & Export
- Click the **"Table"** tab to view a sortable list of all detected features.
- Click **"📄 CSV"** or **"📦 JSON"** to download data files for spreadsheets or external tools.

### 7. Git Tracking & Single-File Database
- **SQLite Database (`data/world_explorer.db`)**: A single self-contained binary file containing all indexed data.
- **Git JSON Dump (`data/world_data.json`)**: Click **"💾 Save for Git"** to checkpoint SQLite and write a lightweight 6 MB JSON file that can be committed and uploaded directly to Git / GitHub repositories without size limit issues.

---

## 🧪 Running Automated Tests

Run the included unit test suite with `pytest`:

```cmd
python -m pytest tests/ -v
```

Tests cover:
- Positive and negative coordinate conversions across block, chunk, and region boundaries
- Binary NBT reader and parser
- MCA region file handling
- Spawner extraction and confidence validation
- Ore vein spatial clustering
- Biome ID resolution and FML registry mapping
- SQLite database transactions, filters, and nearest-feature spatial search

---

## 🛡️ Read-Only Safety Guarantee

The application guarantees:
- Original Minecraft files (`level.dat`, `*.mca`, `playerdata`, `stats`, etc.) are opened strictly with `"rb"` (read-only binary mode).
- No world files are ever written, created, or modified in the Minecraft save folder.
- All application data, caches, and indexes are stored in the self-contained `bmc1-world-explorer/data/` folder.
