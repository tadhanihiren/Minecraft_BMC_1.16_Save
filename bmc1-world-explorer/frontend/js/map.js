/**
 * Plain Canvas Minecraft Map Controller (no Leaflet).
 * One <canvas>, direct pan/zoom, biome chunks as flat color rects,
 * markers drawn as emoji glyphs straight on the canvas. No DOM nodes
 * per marker/chunk, so thousands of features cost one draw() call
 * instead of thousands of Leaflet layers.
 *
 * World coords: x = east, z = south (matches Minecraft; north is up
 * on screen since increasing z already maps to increasing screen Y).
 */

class MinecraftMap {
  constructor(elementId) {
    this.container = document.getElementById(elementId);
    this.container.classList.add("mc-canvas-container");

    this.canvas = document.createElement("canvas");
    this.canvas.className = "mc-canvas";
    this.container.appendChild(this.canvas);
    this.ctx = this.canvas.getContext("2d");

    this.tooltip = document.createElement("div");
    this.tooltip.className = "map-tooltip";
    this.tooltip.hidden = true;
    this.container.appendChild(this.tooltip);

    const zoomControls = document.createElement("div");
    zoomControls.className = "map-zoom-controls";
    zoomControls.innerHTML = `
      <button type="button" class="map-zoom-btn" data-zoom="in" title="Zoom In">+</button>
      <button type="button" class="map-zoom-btn" data-zoom="out" title="Zoom Out">&minus;</button>
    `;
    this.container.appendChild(zoomControls);
    zoomControls.querySelector('[data-zoom="in"]').addEventListener("click", () => this.zoomBy(1.3));
    zoomControls.querySelector('[data-zoom="out"]').addEventListener("click", () => this.zoomBy(1 / 1.3));

    // Camera: (camX, camZ) = world coords at screen center. scale = px per block.
    this.camX = 0;
    this.camZ = 0;
    this.zoomLevel = -2;
    this.scale = Math.pow(2, this.zoomLevel);
    this.minZoomLevel = -6;
    this.maxZoomLevel = 6;

    this.biomeChunks = [];
    this.biomeChunkIndex = new Map();
    this.markers = [];
    this.highlight = null;
    this.player = null;

    this.onLocationSelect = null;
    this.onMouseMove = null;

    this._moveendHandlers = [];
    this._moveendTimer = null;

    // Shims so app.js's existing Leaflet-flavored calls keep working
    // unchanged (mapController.map.invalidateSize/.on, .biomeLayer.clearLayers).
    this.map = {
      invalidateSize: () => this.resize(),
      on: (events, cb) => {
        if (events.includes("moveend") || events.includes("zoomend")) this._moveendHandlers.push(cb);
      },
      getZoom: () => this.zoomLevel
    };
    this.biomeLayer = {
      clearLayers: () => {
        this.biomeChunks = [];
        this.biomeChunkIndex.clear();
        this.draw();
      }
    };

    this._isDragging = false;
    this._dragMoved = 0;
    this._dragStartScreen = [0, 0];
    this._dragStartCam = [0, 0];

    this._resizeObserver = new ResizeObserver(() => this.resize());
    this._resizeObserver.observe(this.container);

    this._bindEvents();
    this.resize();
  }

  // ---- coordinate transforms ----

  worldToScreen(x, z) {
    return [
      this.canvas._cssWidth / 2 + (x - this.camX) * this.scale,
      this.canvas._cssHeight / 2 + (z - this.camZ) * this.scale
    ];
  }

  screenToWorld(px, py) {
    return {
      x: this.camX + (px - this.canvas._cssWidth / 2) / this.scale,
      z: this.camZ + (py - this.canvas._cssHeight / 2) / this.scale
    };
  }

  scheduleMoveEnd() {
    clearTimeout(this._moveendTimer);
    this._moveendTimer = setTimeout(() => {
      this._moveendHandlers.forEach((cb) => cb());
    }, 60);
  }

  // ---- sizing ----

  resize() {
    const rect = this.container.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.canvas._cssWidth = rect.width;
    this.canvas._cssHeight = rect.height;
    this.canvas.width = Math.max(1, Math.round(rect.width * dpr));
    this.canvas.height = Math.max(1, Math.round(rect.height * dpr));
    this.canvas.style.width = rect.width + "px";
    this.canvas.style.height = rect.height + "px";
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.draw();
  }

  // ---- zoom / pan ----

  zoomAt(screenX, screenY, factor) {
    const before = this.screenToWorld(screenX, screenY);
    const newZoomLevel = Math.max(this.minZoomLevel, Math.min(this.maxZoomLevel, this.zoomLevel + Math.log2(factor)));
    this.zoomLevel = newZoomLevel;
    this.scale = Math.pow(2, this.zoomLevel);
    const after = this.screenToWorld(screenX, screenY);
    this.camX += before.x - after.x;
    this.camZ += before.z - after.z;
    this.draw();
    this.scheduleMoveEnd();
  }

  zoomBy(factor) {
    this.zoomAt(this.canvas._cssWidth / 2, this.canvas._cssHeight / 2, factor);
  }

  jumpTo(x, z, zoomLevel) {
    this.camX = x;
    this.camZ = z;
    if (zoomLevel !== undefined) {
      this.zoomLevel = Math.max(this.minZoomLevel, Math.min(this.maxZoomLevel, zoomLevel));
      this.scale = Math.pow(2, this.zoomLevel);
    }
    this.draw();
    this.scheduleMoveEnd();
  }

  renderDynamicGrid() {
    this.draw();
  }

  // ---- viewport bounds (for API bbox queries) ----

  getBlockBounds() {
    const padX = (this.canvas._cssWidth / this.scale) * 0.25;
    const padZ = (this.canvas._cssHeight / this.scale) * 0.25;
    const p1 = this.screenToWorld(0, 0);
    const p2 = this.screenToWorld(this.canvas._cssWidth, this.canvas._cssHeight);
    return {
      minX: Math.round(Math.min(p1.x, p2.x) - padX),
      maxX: Math.round(Math.max(p1.x, p2.x) + padX),
      minZ: Math.round(Math.min(p1.z, p2.z) - padZ),
      maxZ: Math.round(Math.max(p1.z, p2.z) + padZ)
    };
  }

  // ---- data in ----

  renderBiomes(chunkBiomes) {
    this.biomeChunks = chunkBiomes || [];
    this.biomeChunkIndex.clear();
    this.biomeChunks.forEach((c) => this.biomeChunkIndex.set(`${c.chunk_x},${c.chunk_z}`, c));
    this.draw();
  }

  renderMarkers(markers) {
    this.markers = (markers || []).map((m) => {
      if (m.category === "spawner") return { ...m, _icon: this.getSpawnerIcon(m.type), _size: 26 };
      if (m.category === "structure") return { ...m, _icon: this.getStructureIcon(m.type), _size: 28 };
      if (m.category === "chest") return { ...m, _icon: "🎁", _size: 22 };
      if (m.category === "ore") return { ...m, _icon: "💎", _size: 26 };
      return m;
    });
    this.highlight = null;
    this.draw();
  }

  setMarkerCompleted(category, refId, completed) {
    const m = this.markers.find((mk) => mk.category === category && mk.ref_id === refId);
    if (m) {
      m.completed = completed;
      this.draw();
    }
  }

  clearAllMarkers() {
    this.markers = [];
    this.highlight = null;
    this.draw();
  }

  setPlayerMarker(x, z, y) {
    this.player = { x, z, y };
    this.draw();
  }

  clearPlayerMarker() {
    this.player = null;
    this.draw();
  }

  highlightBBox(bbox) {
    this.highlight = bbox && bbox.length >= 6 ? bbox : null;
    this.draw();
  }

  // ---- hit testing ----

  markerAt(px, py) {
    // Reverse order: topmost-drawn (last) marker wins.
    for (let i = this.markers.length - 1; i >= 0; i--) {
      const m = this.markers[i];
      if (m.category === "ore_cluster") {
        const [minX, , minZ, maxX, , maxZ] = m.bbox;
        const [sx1, sy1] = this.worldToScreen(minX, minZ);
        const [sx2, sy2] = this.worldToScreen(maxX + 1, maxZ + 1);
        if (px >= Math.min(sx1, sx2) && px <= Math.max(sx1, sx2) && py >= Math.min(sy1, sy2) && py <= Math.max(sy1, sy2)) {
          return m;
        }
      } else {
        const [sx, sy] = this.worldToScreen(m.x + 0.5, m.z + 0.5);
        const r = (m._size || 26) / 2;
        if (Math.abs(px - sx) <= r && Math.abs(py - sy) <= r) return m;
      }
    }
    return null;
  }

  chunkAt(worldX, worldZ) {
    const cx = Math.floor(worldX / 16);
    const cz = Math.floor(worldZ / 16);
    return this.biomeChunkIndex.get(`${cx},${cz}`);
  }

  // ---- events ----

  _bindEvents() {
    this.canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      const rect = this.canvas.getBoundingClientRect();
      const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
      this.zoomAt(e.clientX - rect.left, e.clientY - rect.top, factor);
    }, { passive: false });

    this.canvas.addEventListener("mousedown", (e) => {
      this._isDragging = true;
      this._dragMoved = 0;
      this._dragStartScreen = [e.clientX, e.clientY];
      this._dragStartCam = [this.camX, this.camZ];
      this.canvas.classList.add("grabbing");
    });

    window.addEventListener("mousemove", (e) => {
      if (this._isDragging) {
        const dx = e.clientX - this._dragStartScreen[0];
        const dz = e.clientY - this._dragStartScreen[1];
        this._dragMoved = Math.max(this._dragMoved, Math.abs(dx), Math.abs(dz));
        this.camX = this._dragStartCam[0] - dx / this.scale;
        this.camZ = this._dragStartCam[1] - dz / this.scale;
        this.draw();
        this.tooltip.hidden = true;
        return;
      }

      const rect = this.canvas.getBoundingClientRect();
      if (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom) {
        this.tooltip.hidden = true;
        return;
      }
      const px = e.clientX - rect.left;
      const py = e.clientY - rect.top;
      const mc = this.screenToWorld(px, py);
      const x = Math.round(mc.x);
      const z = Math.round(mc.z);
      if (this.onMouseMove) {
        this.onMouseMove({ x, z, cx: x >> 4, cz: z >> 4, rx: x >> 9, rz: z >> 9 });
      }
      this._updateTooltip(px, py, mc);
    });

    window.addEventListener("mouseup", (e) => {
      if (!this._isDragging) return;
      this._isDragging = false;
      this.canvas.classList.remove("grabbing");
      if (this._dragMoved > 4) {
        this.scheduleMoveEnd();
        return;
      }
      // Treat as a click.
      const rect = this.canvas.getBoundingClientRect();
      const px = e.clientX - rect.left;
      const py = e.clientY - rect.top;
      this._handleClick(px, py);
    });
  }

  _updateTooltip(px, py, mc) {
    const hit = this.markerAt(px, py);
    let html = null;
    if (hit) {
      html = this._tooltipHtml(hit);
    } else {
      const chunk = this.chunkAt(mc.x, mc.z);
      if (chunk) {
        html = `<b>${chunk.dominant_biome_name}</b><br>Chunk: (${chunk.chunk_x}, ${chunk.chunk_z})`;
      }
    }
    if (html) {
      this.tooltip.innerHTML = html;
      this.tooltip.style.left = px + 14 + "px";
      this.tooltip.style.top = py + 14 + "px";
      this.tooltip.hidden = false;
    } else {
      this.tooltip.hidden = true;
    }
  }

  _tooltipHtml(m) {
    const doneTag = m.completed ? "<br>✅ <i>Completed</i>" : "";
    if (m.category === "ore_cluster") {
      return `💎 <b>${m.name}</b><br>${m.blocks.toLocaleString()} ore blocks in this area<br><i>Zoom in for individual veins</i>`;
    }
    if (m.category === "ore") {
      return `💎 <b>${m.name}</b><br>X: ${m.x}, Y: ${m.y}, Z: ${m.z}<br>Vein: ${m.blocks} blocks${doneTag}`;
    }
    if (m.category === "spawner") {
      return `${m._icon} <b>${m.name}</b><br>X: ${m.x}, Y: ${m.y}, Z: ${m.z}${doneTag}`;
    }
    if (m.category === "structure") {
      return `${m._icon} <b>${m.name}</b><br>X: ${m.x}, Y: ${m.y}, Z: ${m.z}${doneTag}`;
    }
    if (m.category === "chest") {
      let tip = `🎁 <b>Chest</b><br>X: ${m.x}, Y: ${m.y}, Z: ${m.z}`;
      if (m.loot_table) tip += `<br>Loot: ${m.loot_table}`;
      if (m.items && m.items.length) tip += `<br>Items: ${m.items.length}`;
      return tip + doneTag;
    }
    return null;
  }

  _handleClick(px, py) {
    const hit = this.markerAt(px, py);
    if (hit) {
      if (hit.category === "ore_cluster") {
        this.jumpTo(hit.x, hit.z, this.zoomLevel + 2);
        return;
      }
      if (hit.bbox) this.highlightBBox(hit.bbox);
      if (this.onLocationSelect) this.onLocationSelect(hit);
      return;
    }
    const mc = this.screenToWorld(px, py);
    if (this.onLocationSelect) {
      this.onLocationSelect({
        category: "point",
        name: "Map Location",
        x: Math.round(mc.x),
        y: 64,
        z: Math.round(mc.z),
        source: "Arbitrary Point",
        confidence: "HIGH"
      });
    }
  }

  // ---- drawing ----

  draw() {
    const ctx = this.ctx;
    const w = this.canvas._cssWidth;
    const h = this.canvas._cssHeight;
    ctx.clearRect(0, 0, w, h);

    // Biome chunks (flat color squares).
    this.biomeChunks.forEach((chunk) => {
      const minX = chunk.chunk_x * 16;
      const minZ = chunk.chunk_z * 16;
      const [sx, sy] = this.worldToScreen(minX, minZ);
      const size = 16 * this.scale;
      ctx.fillStyle = this.getBiomeColor(chunk.dominant_biome_id);
      ctx.globalAlpha = 0.35;
      ctx.fillRect(sx, sy, size, size);
    });
    ctx.globalAlpha = 1;

    // Block grid (every 1 block) — faint, lighter than chunk borders, only
    // once individual blocks are actually big enough on screen to matter.
    if (this.scale >= 12) {
      const bounds = this.getBlockBounds();
      const minX = Math.floor(bounds.minX);
      const maxX = Math.ceil(bounds.maxX);
      const minZ = Math.floor(bounds.minZ);
      const maxZ = Math.ceil(bounds.maxZ);
      ctx.strokeStyle = "rgba(0, 0, 0, 0.18)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = minX; x <= maxX; x += 1) {
        const [sx1, sy1] = this.worldToScreen(x, minZ);
        const [sx2, sy2] = this.worldToScreen(x, maxZ);
        ctx.moveTo(sx1, sy1);
        ctx.lineTo(sx2, sy2);
      }
      for (let z = minZ; z <= maxZ; z += 1) {
        const [sx1, sy1] = this.worldToScreen(minX, z);
        const [sx2, sy2] = this.worldToScreen(maxX, z);
        ctx.moveTo(sx1, sy1);
        ctx.lineTo(sx2, sy2);
      }
      ctx.stroke();
    }

    // Chunk borders (every 16 blocks) — solid dark lines, deliberately
    // darker than any biome fill color so chunk boundaries stay readable
    // regardless of theme. Only drawn once zoomed in enough that 16-block
    // cells are actually legible; otherwise this is thousands of
    // sub-pixel lines for no visual gain.
    if (this.scale >= 2) {
      const bounds = this.getBlockBounds();
      const minCX = Math.floor(bounds.minX / 16) * 16;
      const maxCX = Math.ceil(bounds.maxX / 16) * 16;
      const minCZ = Math.floor(bounds.minZ / 16) * 16;
      const maxCZ = Math.ceil(bounds.maxZ / 16) * 16;
      ctx.strokeStyle = "rgba(0, 0, 0, 0.55)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = minCX; x <= maxCX; x += 16) {
        const [sx1, sy1] = this.worldToScreen(x, minCZ);
        const [sx2, sy2] = this.worldToScreen(x, maxCZ);
        ctx.moveTo(sx1, sy1);
        ctx.lineTo(sx2, sy2);
      }
      for (let z = minCZ; z <= maxCZ; z += 16) {
        const [sx1, sy1] = this.worldToScreen(minCX, z);
        const [sx2, sy2] = this.worldToScreen(maxCX, z);
        ctx.moveTo(sx1, sy1);
        ctx.lineTo(sx2, sy2);
      }
      ctx.stroke();
    }

    // Markers.
    this.markers.forEach((m) => {
      if (m.category === "ore_cluster") {
        // Dark navy at max zoom-out instead of the old light cyan — reads
        // clearly against light and dark biome fills alike.
        const [minX, , minZ, maxX, , maxZ] = m.bbox;
        const [sx1, sy1] = this.worldToScreen(minX, minZ);
        const [sx2, sy2] = this.worldToScreen(maxX + 1, maxZ + 1);
        ctx.fillStyle = "#0c3a52";
        ctx.globalAlpha = Math.min(0.75, 0.25 + m.vein_count / 200);
        ctx.fillRect(Math.min(sx1, sx2), Math.min(sy1, sy2), Math.abs(sx2 - sx1), Math.abs(sy2 - sy1));
        ctx.globalAlpha = 1;
        ctx.strokeStyle = "#062533";
        ctx.lineWidth = 1;
        ctx.strokeRect(Math.min(sx1, sx2), Math.min(sy1, sy2), Math.abs(sx2 - sx1), Math.abs(sy2 - sy1));
      } else if (m.category === "ore") {
        // Plain dark square instead of the diamond emoji — per-ore-type
        // color still shown via the border, but the fill stays dark so
        // veins don't visually compete with spawner/structure icons.
        const [sx, sy] = this.worldToScreen(m.x + 0.5, m.z + 0.5);
        const size = Math.max(6, (m._size || 26) * 0.6);
        ctx.globalAlpha = m.completed ? 0.35 : 1;
        ctx.fillStyle = "#12222b";
        ctx.fillRect(sx - size / 2, sy - size / 2, size, size);
        ctx.strokeStyle = this.getOreColor(m.type);
        ctx.lineWidth = 1.5;
        ctx.strokeRect(sx - size / 2, sy - size / 2, size, size);
        ctx.globalAlpha = 1;
        if (m.completed) {
          ctx.font = `${Math.round(size * 0.9)}px sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText("✅", sx + size * 0.4, sy + size * 0.4);
        }
      } else {
        const [sx, sy] = this.worldToScreen(m.x + 0.5, m.z + 0.5);
        const size = m._size || 26;
        ctx.font = `${size}px "Segoe UI Emoji", "Noto Color Emoji", sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.shadowColor = "rgba(0, 0, 0, 0.45)";
        ctx.shadowBlur = 2;
        ctx.globalAlpha = m.completed ? 0.35 : 1;
        ctx.fillText(m._icon || "❔", sx, sy);
        ctx.globalAlpha = 1;
        ctx.shadowBlur = 0;
        if (m.completed) {
          ctx.font = `${Math.round(size * 0.55)}px sans-serif`;
          ctx.fillText("✅", sx + size * 0.32, sy + size * 0.32);
        }
      }
    });

    // Highlight bbox for the selected feature.
    if (this.highlight) {
      const [minX, , minZ, maxX, , maxZ] = this.highlight;
      const [sx1, sy1] = this.worldToScreen(minX, minZ);
      const [sx2, sy2] = this.worldToScreen(maxX, maxZ);
      ctx.strokeStyle = "#f59e0b";
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(Math.min(sx1, sx2), Math.min(sy1, sy2), Math.abs(sx2 - sx1), Math.abs(sy2 - sy1));
      ctx.setLineDash([]);
    }

    // Player marker.
    if (this.player) {
      const [sx, sy] = this.worldToScreen(this.player.x, this.player.z);
      ctx.font = `28px "Segoe UI Emoji", "Noto Color Emoji", sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.shadowColor = "rgba(0, 0, 0, 0.45)";
      ctx.shadowBlur = 3;
      ctx.fillText("🧍", sx, sy - 12);
      ctx.shadowBlur = 0;
    }
  }

  // ---- icon / color lookups (unchanged from the previous Leaflet build) ----

  getSpawnerIcon(entityId) {
    const id = (entityId || "").replace("minecraft:", "").toLowerCase();
    const icons = {
      zombie: "🧟", zombie_villager: "🧟", husk: "🧟", drowned: "🌊",
      skeleton: "💀", wither_skeleton: "☠️", stray: "💀",
      spider: "🕷️", cave_spider: "🕸️", silverfish: "🐛",
      vex: "👻", vindicator: "🪓", pillager: "🏹", witch: "🧙",
      piglin_brute: "🐷", creeper: "💥", enderman: "👤",
      slime: "🟩", magma_cube: "🟧", blaze: "🔥", ghast: "😱",
      guardian: "🐟", elder_guardian: "🐟", snow_golem: "⛄",
      chicken: "🐔", cow: "🐄", pig: "🐖", sheep: "🐑",
      cod: "🐟", salmon: "🐟", pufferfish: "🐡", dolphin: "🐬",
      squid: "🦑", parrot: "🦜"
    };
    return icons[id] || "👾";
  }

  getStructureIcon(structureId) {
    const id = (structureId || "").toLowerCase();
    if (id.includes("village")) return "🏘️";
    if (id.includes("stronghold")) return "🏛️";
    if (id.includes("monument")) return "🌊";
    if (id.includes("mansion")) return "🏚️";
    if (id.includes("outpost")) return "🏹";
    if (id.includes("mineshaft")) return "⛏️";
    if (id.includes("dungeon")) return "⚔️";
    if (id.includes("portal")) return "🌀";
    if (id.includes("pyramid") || id.includes("temple")) return "⛩️";
    if (id.includes("shipwreck") || id.includes("ship") || id.includes("galley") || id.includes("corsair")) return "🚢";
    if (id.includes("igloo")) return "🧊";
    if (id.includes("ruin")) return "🗿";
    if (id.includes("treasure")) return "💰";
    if (id.includes("well")) return "🪣";
    if (id.includes("windmill")) return "🎡";
    if (id.includes("tower")) return "🗼";
    if (id.includes("hut") || id.includes("house") || id.includes("campsite")) return "🛖";
    return "🏰";
  }

  getOreColor(oreId) {
    const id = (oreId || "").toLowerCase();
    if (id.includes("diamond")) return "#00f0ff";
    if (id.includes("emerald")) return "#10b981";
    if (id.includes("debris")) return "#a855f7";
    if (id.includes("gold")) return "#f59e0b";
    if (id.includes("iron")) return "#cbd5e1";
    if (id.includes("copper")) return "#f97316";
    if (id.includes("lapis")) return "#3b82f6";
    if (id.includes("redstone")) return "#ef4444";
    if (id.includes("coal")) return "#64748b";
    if (id.includes("quartz")) return "#f8fafc";
    if (id.includes("silver")) return "#e5e7eb";
    return "#38bdf8";
  }

  getBiomeColor(biomeId) {
    const id = (biomeId || "").toLowerCase();
    if (id.includes("ocean") || id.includes("river") || id.includes("lake")) return "#1e3a8a";
    if (id.includes("desert") || id.includes("dunes") || id.includes("beach")) return "#ca8a04";
    if (id.includes("taiga") || id.includes("coniferous")) return "#14532d";
    if (id.includes("forest") || id.includes("woods") || id.includes("grove")) return "#166534";
    if (id.includes("plains") || id.includes("meadow")) return "#15803d";
    if (id.includes("swamp") || id.includes("bayou") || id.includes("marsh")) return "#3f6212";
    if (id.includes("jungle") || id.includes("tropics")) return "#047857";
    if (id.includes("mountain") || id.includes("peak") || id.includes("hills")) return "#475569";
    if (id.includes("snow") || id.includes("frozen") || id.includes("glacier") || id.includes("ice")) return "#93c5fd";
    if (id.includes("nether") || id.includes("crimson") || id.includes("basalt")) return "#7f1d1d";
    if (id.includes("end")) return "#581c87";
    return "#334155";
  }
}
