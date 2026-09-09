/**
 * Leaflet Minecraft Map Controller
 * Uses L.CRS.Simple for Minecraft block coordinates (X -> Lng, Z -> -Lat)
 */

class MinecraftMap {
  constructor(elementId) {
    this.map = L.map(elementId, {
      crs: L.CRS.Simple,
      minZoom: -5,
      maxZoom: 4,
      zoomSnap: 0.5,
      zoomDelta: 0.5,
      attributionControl: false,
      zoomControl: false,
      preferCanvas: true
    });

    L.control.zoom({ position: "bottomright" }).addTo(this.map);

    // Layer Groups
    this.gridLayer = L.layerGroup().addTo(this.map);
    this.biomeLayer = L.layerGroup().addTo(this.map);
    this.oreLayer = L.layerGroup().addTo(this.map);
    this.spawnerLayer = L.layerGroup().addTo(this.map);
    this.structureLayer = L.layerGroup().addTo(this.map);
    this.chestLayer = L.layerGroup().addTo(this.map);
    this.highlightLayer = L.layerGroup().addTo(this.map);
    this.playerLayer = L.layerGroup().addTo(this.map);

    // Initial center at 0, 0 with zoom -2 (covers ~2000 blocks)
    this.map.setView([0, 0], -2);

    this.onLocationSelect = null;
    this.onMouseMove = null;

    this.initEvents();
    this.drawGrid();
  }

  mcToLatLng(x, z) {
    // Invert Z so North (-Z) is Up (+lat)
    return L.latLng(-z, x);
  }

  latLngToMc(latlng) {
    return {
      x: Math.round(latlng.lng),
      z: Math.round(-latlng.lat)
    };
  }

  drawGrid() {
    this.map.on("moveend zoomend", () => {
      this.renderDynamicGrid();
    });
    this.renderDynamicGrid();
  }

  renderDynamicGrid() {
    this.gridLayer.clearLayers();
    const bounds = this.map.getBounds();
    const minX = Math.floor(bounds.getWest() / 512) * 512;
    const maxX = Math.ceil(bounds.getEast() / 512) * 512;
    const minZ = Math.floor(-bounds.getNorth() / 512) * 512;
    const maxZ = Math.ceil(-bounds.getSouth() / 512) * 512;

    // Read the current theme's grid-line color from CSS so this stays in
    // sync with the dark/light toggle without duplicating color logic here.
    const lineColor = getComputedStyle(document.documentElement).getPropertyValue("--map-line").trim() || "rgba(0, 229, 255, 0.09)";

    // Draw region lines (512x512 blocks)
    const zoom = this.map.getZoom();
    if (zoom >= -4) {
      for (let x = minX; x <= maxX; x += 512) {
        const p1 = this.mcToLatLng(x, minZ);
        const p2 = this.mcToLatLng(x, maxZ);
        L.polyline([p1, p2], {
          color: lineColor,
          weight: 1,
          dashArray: "2, 4"
        }).addTo(this.gridLayer);
      }
      for (let z = minZ; z <= maxZ; z += 512) {
        const p1 = this.mcToLatLng(minX, z);
        const p2 = this.mcToLatLng(maxX, z);
        L.polyline([p1, p2], {
          color: lineColor,
          weight: 1,
          dashArray: "2, 4"
        }).addTo(this.gridLayer);
      }
    }
  }

  initEvents() {
    this.map.on("mousemove", (e) => {
      const mc = this.latLngToMc(e.latlng);
      const cx = mc.x >> 4;
      const cz = mc.z >> 4;
      const rx = mc.x >> 9;
      const rz = mc.z >> 9;
      if (this.onMouseMove) {
        this.onMouseMove({ x: mc.x, z: mc.z, cx, cz, rx, rz });
      }
    });

    this.map.on("click", (e) => {
      const mc = this.latLngToMc(e.latlng);
      if (this.onLocationSelect) {
        this.onLocationSelect({
          category: "point",
          name: "Map Location",
          x: mc.x,
          y: 64,
          z: mc.z,
          source: "Arbitrary Point",
          confidence: "HIGH"
        });
      }
    });
  }

  // Current visible viewport in Minecraft block coordinates, padded a bit
  // so panning slightly doesn't immediately show empty edges.
  getBlockBounds() {
    const b = this.map.getBounds().pad(0.25);
    const p1 = this.latLngToMc(b.getSouthWest());
    const p2 = this.latLngToMc(b.getNorthEast());
    return {
      minX: Math.min(p1.x, p2.x),
      maxX: Math.max(p1.x, p2.x),
      minZ: Math.min(p1.z, p2.z),
      maxZ: Math.max(p1.z, p2.z)
    };
  }

  // Exact-footprint markers rendered as canvas L.rectangles (not DOM
  // divIcons) — thousands of these cost almost nothing to draw or pan.
  // No invented "small/big" sizing: a single-block feature draws at
  // exactly 1x1 block, and a multi-block feature (ore vein, structure)
  // draws its real bounding box. Both are in world (block) units, so on
  // screen they naturally get bigger when you zoom in and smaller when
  // you zoom out — that's the map zooming, not the marker being resized.

  // One exact Minecraft block at (x, z). L.latLngBounds normalizes the
  // two corners itself, so which one is "north/south" doesn't matter.
  exactBlockMarker(x, z, style) {
    const p1 = this.mcToLatLng(x, z);
    const p2 = this.mcToLatLng(x + 1, z + 1);
    return L.rectangle(L.latLngBounds(p1, p2), this._rectStyle(style));
  }

  // The feature's real bounding box, e.g. an ore vein's or structure's
  // [minX, minY, minZ, maxX, maxY, maxZ] from the scanner. +1 on the max
  // corner so a single-block-wide vein still draws a full block, not a
  // zero-width line.
  exactBboxMarker(bbox, style) {
    const [minX, , minZ, maxX, , maxZ] = bbox;
    const p1 = this.mcToLatLng(minX, minZ);
    const p2 = this.mcToLatLng(maxX + 1, maxZ + 1);
    return L.rectangle(L.latLngBounds(p1, p2), this._rectStyle(style));
  }

  _rectStyle({ fillColor, strokeColor, opacity = 0.9, weight = 1.5 }) {
    return { color: strokeColor, weight, fillColor, fillOpacity: opacity };
  }

  jumpTo(x, z, zoom = 0) {
    const latlng = this.mcToLatLng(x, z);
    this.map.setView(latlng, zoom);
  }

  // Drop (or move) a marker showing the player's current coordinates.
  setPlayerMarker(x, z, y) {
    this.playerLayer.clearLayers();
    const latlng = this.mcToLatLng(x, z);
    const icon = L.divIcon({
      className: "player-marker-icon",
      html: '<div class="player-pin">🧍</div>',
      iconSize: [28, 28],
      iconAnchor: [14, 26]
    });
    const marker = L.marker(latlng, { icon, zIndexOffset: 1000 });
    marker.bindTooltip(`📍 <b>You are here</b><br>X: ${x}, Y: ${y !== undefined ? y : 64}, Z: ${z}`);
    marker.addTo(this.playerLayer);
  }

  clearPlayerMarker() {
    this.playerLayer.clearLayers();
  }

  highlightBBox(bbox) {
    this.highlightLayer.clearLayers();
    if (!bbox || bbox.length < 6) return;
    const [minX, minY, minZ, maxX, maxY, maxZ] = bbox;
    const p1 = this.mcToLatLng(minX, minZ);
    const p2 = this.mcToLatLng(maxX, maxZ);
    const bounds = L.latLngBounds(p1, p2);
    L.rectangle(bounds, {
      color: "#f59e0b",
      weight: 2,
      dashArray: "4, 4",
      fillOpacity: 0.12
    }).addTo(this.highlightLayer);
  }

  clearAllMarkers() {
    this.oreLayer.clearLayers();
    this.spawnerLayer.clearLayers();
    this.structureLayer.clearLayers();
    this.chestLayer.clearLayers();
    this.highlightLayer.clearLayers();
  }

  renderBiomes(chunkBiomes) {
    this.biomeLayer.clearLayers();
    // Binding a tooltip to every chunk rectangle is what makes a
    // whole-world (zoomed-out) view feel frozen — thousands of hit-test
    // targets on top of thousands of shapes. Skip tooltips above a
    // threshold; the shapes still render instantly either way.
    const withTooltips = chunkBiomes.length <= 1500;

    chunkBiomes.forEach((chunk) => {
      const minX = chunk.chunk_x * 16;
      const minZ = chunk.chunk_z * 16;
      const p1 = this.mcToLatLng(minX, minZ);
      const p2 = this.mcToLatLng(minX + 16, minZ + 16);
      const bounds = L.latLngBounds(p1, p2);

      const color = this.getBiomeColor(chunk.dominant_biome_id);
      const rect = L.rectangle(bounds, {
        color: color,
        weight: 0.5,
        opacity: 0.35,
        fillColor: color,
        fillOpacity: 0.22,
        interactive: withTooltips
      });

      if (withTooltips) {
        rect.bindTooltip(`<b>${chunk.dominant_biome_name}</b><br>Chunk: (${chunk.chunk_x}, ${chunk.chunk_z})`, {
          sticky: true
        });
      }

      rect.addTo(this.biomeLayer);
    });
  }

  renderMarkers(markers) {
    this.clearAllMarkers();

    markers.forEach((m) => {
      if (m.category === "ore_cluster") {
        // Zoomed-out density cluster standing in for many individual ore
        // veins in this cell (see backend get_markers) — a translucent
        // cyan cell scaled by how much ore it holds, not a real vein color.
        const marker = this.exactBboxMarker(m.bbox, {
          fillColor: "#38bdf8",
          strokeColor: "#0ea5e9",
          opacity: Math.min(0.6, 0.15 + m.vein_count / 200),
          weight: 1
        });
        marker.bindTooltip(`💎 <b>${m.name}</b><br>${m.blocks.toLocaleString()} ore blocks in this area<br><i>Zoom in for individual veins</i>`);
        marker.on("click", (e) => {
          L.DomEvent.stopPropagation(e);
          this.jumpTo(m.x, m.z, this.map.getZoom() + 2);
        });
        marker.addTo(this.oreLayer);

      } else if (m.category === "ore") {
        const fillColor = this.getOreColor(m.type);
        // Iron/quartz render pale on purpose (their real color), which
        // nearly disappears against a light map background — give those
        // two a fixed mid-tone stroke so the marker stays legible in both
        // the dark and light theme, while keeping the true fill color.
        const isPaleOre = /iron|quartz/.test((m.type || "").toLowerCase());
        const style = {
          fillColor: fillColor,
          strokeColor: isPaleOre ? "#64748b" : fillColor,
          opacity: 0.85,
          weight: 1.5
        };
        const marker = m.bbox ? this.exactBboxMarker(m.bbox, style) : this.exactBlockMarker(m.x, m.z, style);

        marker.bindTooltip(`💎 <b>${m.name}</b><br>X: ${m.x}, Y: ${m.y}, Z: ${m.z}<br>Vein: ${m.blocks} blocks`);
        marker.on("click", (e) => {
          L.DomEvent.stopPropagation(e);
          if (m.bbox) this.highlightBBox(m.bbox);
          if (this.onLocationSelect) this.onLocationSelect(m);
        });
        marker.addTo(this.oreLayer);

      } else if (m.category === "spawner") {
        const marker = this.exactBlockMarker(m.x, m.z, {
          fillColor: "#f87171",
          strokeColor: "#ef4444",
          weight: 2
        });

        marker.bindTooltip(`🧟 <b>${m.name}</b><br>X: ${m.x}, Y: ${m.y}, Z: ${m.z}`);
        marker.on("click", (e) => {
          L.DomEvent.stopPropagation(e);
          if (this.onLocationSelect) this.onLocationSelect(m);
        });
        marker.addTo(this.spawnerLayer);

      } else if (m.category === "structure") {
        const style = { fillColor: "#fbbf24", strokeColor: "#f59e0b", weight: 2 };
        const marker = m.bbox ? this.exactBboxMarker(m.bbox, style) : this.exactBlockMarker(m.x, m.z, style);

        marker.bindTooltip(`🏰 <b>${m.name}</b><br>X: ${m.x}, Y: ${m.y}, Z: ${m.z}`);
        marker.on("click", (e) => {
          L.DomEvent.stopPropagation(e);
          if (m.bbox) this.highlightBBox(m.bbox);
          if (this.onLocationSelect) this.onLocationSelect(m);
        });
        marker.addTo(this.structureLayer);

      } else if (m.category === "chest") {
        const marker = this.exactBlockMarker(m.x, m.z, {
          fillColor: "#c084fc",
          strokeColor: "#a855f7",
          weight: 1.5
        });

        let tip = `🎁 <b>Chest</b><br>X: ${m.x}, Y: ${m.y}, Z: ${m.z}`;
        if (m.loot_table) tip += `<br>Loot: ${m.loot_table}`;
        if (m.items && m.items.length) tip += `<br>Items: ${m.items.length}`;
        marker.bindTooltip(tip);

        marker.on("click", (e) => {
          L.DomEvent.stopPropagation(e);
          if (this.onLocationSelect) this.onLocationSelect(m);
        });
        marker.addTo(this.chestLayer);
      }
    });
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
