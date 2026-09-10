/**
 * Modern Application Logic for BMC1 World Explorer
 * Layers are UNCHECKED by default to prevent visual clutter and lag.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Theme toggle (light Atlas look by default, dark variant on request).
  const btnThemeToggle = document.getElementById("btnThemeToggle");
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("bmc1_theme", theme);
    btnThemeToggle.innerText = theme === "light" ? "☀️" : "🌙";
    // Grid line color is read from CSS at draw time, so nudge a redraw
    // now instead of waiting for the next pan/zoom.
    if (typeof mapController !== "undefined") mapController.renderDynamicGrid();
  }
  const savedTheme = document.documentElement.getAttribute("data-theme")
    || (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", savedTheme);
  btnThemeToggle.innerText = savedTheme === "light" ? "☀️" : "🌙";
  btnThemeToggle.addEventListener("click", () => {
    const next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
    applyTheme(next);
  });

  const mapController = new MinecraftMap("map");

  // State: NOTHING selected by default
  let currentWorld = null;
  let currentDimension = "minecraft:overworld";
  let activeFilters = {
    biomes: false,
    ores: false,
    spawners: false,
    structures: false,
    chests: false,
    oreTypes: [],
    spawnerTypes: [],
    structureTypes: []
  };
  let pollInterval = null;

  // DOM Elements
  const worldNameEl = document.getElementById("worldName");
  const worldSeedEl = document.getElementById("worldSeed");
  const dimSelector = document.getElementById("dimensionSelect");
  const btnScan = document.getElementById("btnScan");
  const btnForceRescan = document.getElementById("btnForceRescan");
  const btnCancelScan = document.getElementById("btnCancelScan");
  const scanBar = document.getElementById("scanBar");
  const scanProgressFill = document.getElementById("scanProgressFill");
  const scanPercentEl = document.getElementById("scanPercent");
  const scanStatusEl = document.getElementById("scanStatus");
  const hudCoords = document.getElementById("hudCoords");
  const mapHintBanner = document.getElementById("mapHintBanner");
  const sidebar = document.getElementById("sidebar");
  const btnToggleSidebar = document.getElementById("btnToggleSidebar");

  // Selected Card
  const selectedPanel = document.getElementById("selectedPanel");
  const selectedTitle = document.getElementById("selectedTitle");
  const selectedCoords = document.getElementById("selectedCoords");
  const selectedMeta = document.getElementById("selectedMeta");
  const selIcon = document.getElementById("selIcon");
  const btnCopyCoords = document.getElementById("btnCopyCoords");
  const btnCopyTp = document.getElementById("btnCopyTp");
  const btnMarkCompleted = document.getElementById("btnMarkCompleted");
  const searchInput = document.getElementById("searchInput");
  const searchResults = document.getElementById("searchResults");
  const toast = document.getElementById("toast");

  let selectedLocation = null;

  // Sidebar Collapse Toggle
  btnToggleSidebar.addEventListener("click", () => {
    sidebar.classList.toggle("collapsed");
    const isCollapsed = sidebar.classList.contains("collapsed");
    btnToggleSidebar.innerText = isCollapsed ? "▶" : "◀";
    setTimeout(() => {
      mapController.resize();
    }, 260);
  });

  // Map Hover HUD
  mapController.onMouseMove = (pos) => {
    hudCoords.innerHTML = `X: <span>${pos.x}</span>  Z: <span>${pos.z}</span>  •  Chunk: <span>(${pos.cx}, ${pos.cz})</span>  •  Region: <span>r.${pos.rx}.${pos.rz}.mca</span>`;
  };

  // Re-render the visible layers when the viewport settles (pan/zoom), so
  // only on-screen data is ever fetched instead of the whole world at once.
  let viewportRefreshTimer = null;
  mapController.onViewportSettled = () => {
    clearTimeout(viewportRefreshTimer);
    viewportRefreshTimer = setTimeout(() => refreshMap(), 200);
  };

  // Map Click Selection
  mapController.onLocationSelect = (loc) => {
    selectedLocation = loc;
    selectedPanel.style.display = "flex";
    selectedTitle.innerText = loc.name || "Selected Location";
    selectedCoords.innerText = `X: ${loc.x}  Y: ${loc.y !== undefined ? loc.y : 64}  Z: ${loc.z}`;
    selectedMeta.innerText = `${(loc.category || "Point").toUpperCase()} • ${loc.source || "Map Point"} • ${loc.confidence || "HIGH"}`;

    if (loc.category === "spawner") selIcon.innerText = "🧟";
    else if (loc.category === "ore") selIcon.innerText = "💎";
    else if (loc.category === "structure") selIcon.innerText = "🏰";
    else if (loc.category === "chest") selIcon.innerText = "🎁";
    else selIcon.innerText = "📍";

    const canComplete = loc.ref_id !== undefined && ["ore", "spawner", "structure", "chest"].includes(loc.category);
    btnMarkCompleted.style.display = canComplete ? "inline-flex" : "none";
    btnMarkCompleted.classList.toggle("btn-completed", !!loc.completed);
    btnMarkCompleted.innerText = loc.completed ? "✅ Completed" : "☐ Mark Completed";
  };

  // Toggle a marker's completed (mined/looted/cleared) state, dim it on
  // the map with a checkmark badge, and persist it in the DB so it
  // survives reloads/rescans.
  btnMarkCompleted.addEventListener("click", async () => {
    if (!selectedLocation || selectedLocation.ref_id === undefined) return;
    try {
      const res = await fetch("/api/map/markers/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dimension: currentDimension,
          category: selectedLocation.category,
          ref_id: selectedLocation.ref_id
        })
      });
      const data = await res.json();
      selectedLocation.completed = data.completed;
      btnMarkCompleted.classList.toggle("btn-completed", !!data.completed);
      btnMarkCompleted.innerText = data.completed ? "✅ Completed" : "☐ Mark Completed";
      mapController.setMarkerCompleted(selectedLocation.category, selectedLocation.ref_id, data.completed);
      showToast(data.completed ? "Marked completed" : "Marked not completed");
    } catch (e) {
      console.error("Error toggling completed:", e);
    }
  });

  // Toast Helper
  function showToast(msg) {
    toast.innerText = msg;
    toast.style.display = "block";
    setTimeout(() => {
      toast.style.display = "none";
    }, 2200);
  }

  // Copy Buttons
  btnCopyCoords.addEventListener("click", () => {
    if (!selectedLocation) return;
    const y = selectedLocation.y !== undefined ? selectedLocation.y : 64;
    const text = `${selectedLocation.x} ${y} ${selectedLocation.z}`;
    navigator.clipboard.writeText(text);
    showToast(`Copied Coordinates: ${text}`);
  });

  btnCopyTp.addEventListener("click", () => {
    if (!selectedLocation) return;
    const y = selectedLocation.y !== undefined ? selectedLocation.y : 64;
    const text = `/tp @s ${selectedLocation.x} ${y} ${selectedLocation.z}`;
    navigator.clipboard.writeText(text);
    showToast(`Copied: ${text}`);
  });

  // Copy Seed
  worldSeedEl.addEventListener("click", () => {
    if (currentWorld && currentWorld.seed) {
      navigator.clipboard.writeText(String(currentWorld.seed));
      showToast(`Copied Seed: ${currentWorld.seed}`);
    }
  });

  // Load World
  async function loadCurrentWorld() {
    try {
      const res = await fetch("/api/worlds/current");
      const data = await res.json();
      if (data && data.world_path) {
        currentWorld = data;
        worldNameEl.innerText = data.world_name || "Unknown World";
        worldSeedEl.innerText = data.seed ? `Seed: ${data.seed}` : "Seed: Unknown";
        if (worldPathInput && !worldPathInput.value) worldPathInput.value = data.world_path;

        // Populate Dimensions
        dimSelector.innerHTML = "";
        data.dimensions.forEach((d) => {
          const opt = document.createElement("option");
          opt.value = d.id;
          let icon = "🌌";
          if (d.id.includes("overworld")) icon = "🌲";
          else if (d.id.includes("nether")) icon = "🔥";
          else if (d.id.includes("end")) icon = "🔮";
          opt.innerText = `${icon} ${d.name}`;
          dimSelector.appendChild(opt);
        });

        if (data.spawn) {
          mapController.jumpTo(data.spawn.x, data.spawn.z, -2);
        }

        await updateStats();
        await loadFilterOptions();
        await refreshMap();
      }
    } catch (e) {
      console.error("Error loading world:", e);
    }
  }

  // Dimension Change
  dimSelector.addEventListener("change", async (e) => {
    currentDimension = e.target.value;
    await updateStats();
    await loadFilterOptions();
    await refreshMap();
  });

  // Accordion Header Click: expand/collapse sub-filters
  document.querySelectorAll(".category-header[data-toggle]").forEach((header) => {
    header.addEventListener("click", () => {
      const targetId = header.dataset.toggle;
      const target = document.getElementById(targetId);
      if (target) {
        target.classList.toggle("open");
      }
    });
  });

  // Categories with no sub-filter drawer (Chests, Biomes) have nothing
  // else to do on a header click, so the tiny switch was the only hit
  // target — let the whole row toggle the layer too. The switch's own
  // click already stops propagation, so this never double-toggles it.
  document.querySelectorAll(".category-header:not([data-toggle])").forEach((header) => {
    header.addEventListener("click", () => {
      const checkbox = header.querySelector('input[type="checkbox"]');
      if (checkbox) {
        checkbox.checked = !checkbox.checked;
        checkbox.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
  });

  // Load Filter Options & Render Filter Chips (unselected by default)
  async function loadFilterOptions() {
    try {
      const res = await fetch(`/api/map/filter_options?dimension=${encodeURIComponent(currentDimension)}`);
      const data = await res.json();

      renderChips("oreChipsContainer", data.ores || [], "oreTypes", "chkOres", "subOres");
      renderChips("spawnerChipsContainer", data.spawners || [], "spawnerTypes", "chkSpawners", "subSpawners");
      renderChips("structureChipsContainer", data.structures || [], "structureTypes", "chkStructures", "subStructures");
    } catch (e) {
      console.error("Error loading filter options:", e);
    }
  }

  function renderChips(containerId, items, activeArrayKey, masterSwitchId, subfilterBodyId) {
    const container = document.getElementById(containerId);
    container.innerHTML = "";
    if (!items.length) {
      container.innerHTML = `<span style="font-size: 11px; color: var(--text-muted);">None found in this dimension</span>`;
      return;
    }

    items.forEach((item) => {
      const chip = document.createElement("span");
      chip.className = "filter-chip";
      // Re-rendering chips (dimension switch, rescan) previously wiped
      // out .active state while activeFilters[activeArrayKey] kept the
      // old selection — chip highlighting and the actual filter drifted
      // out of sync. Restore active state from the existing filter list.
      if (activeFilters[activeArrayKey].includes(item.id)) {
        chip.classList.add("active");
      }
      chip.innerText = item.name;
      chip.dataset.id = item.id;

      chip.addEventListener("click", (e) => {
        e.stopPropagation();
        chip.classList.toggle("active");

        // Sync with activeArrayKey
        const selected = Array.from(container.querySelectorAll(".filter-chip.active")).map((c) => c.dataset.id);
        activeFilters[activeArrayKey] = selected;

        // Auto-enable master switch if a sub-filter chip is clicked
        const masterSwitch = document.getElementById(masterSwitchId);
        if (selected.length > 0 && !masterSwitch.checked) {
          masterSwitch.checked = true;
          const key = masterSwitchId.replace("chk", "").toLowerCase();
          activeFilters[key] = true;
        } else if (selected.length === 0) {
          // If no chips selected, keep master filter behavior
        }
        refreshMap();
      });

      container.appendChild(chip);
    });
  }

  // Select All / None inside sub-filters
  setupBulkChipButtons("btnSelectAllOres", "btnClearAllOres", "oreChipsContainer", "oreTypes", "chkOres");
  setupBulkChipButtons("btnSelectAllSpawners", "btnClearAllSpawners", "spawnerChipsContainer", "spawnerTypes", "chkSpawners");
  setupBulkChipButtons("btnSelectAllStructures", "btnClearAllStructures", "structureChipsContainer", "structureTypes", "chkStructures");

  function setupBulkChipButtons(btnAllId, btnNoneId, containerId, activeArrayKey, masterSwitchId) {
    const btnAll = document.getElementById(btnAllId);
    const btnNone = document.getElementById(btnNoneId);
    const container = document.getElementById(containerId);

    if (btnAll) {
      btnAll.addEventListener("click", (e) => {
        e.stopPropagation();
        container.querySelectorAll(".filter-chip").forEach((c) => c.classList.add("active"));
        activeFilters[activeArrayKey] = Array.from(container.querySelectorAll(".filter-chip")).map((c) => c.dataset.id);
        const sw = document.getElementById(masterSwitchId);
        sw.checked = true;
        activeFilters[masterSwitchId.replace("chk", "").toLowerCase()] = true;
        refreshMap();
      });
    }

    if (btnNone) {
      btnNone.addEventListener("click", (e) => {
        e.stopPropagation();
        container.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
        activeFilters[activeArrayKey] = [];
        refreshMap();
      });
    }
  }

  // Master toggle <-> sub-filter chips: turning a category off clears
  // every chip in it, turning it on selects every chip — the master
  // switch always reflects "all" or "none", never a stale partial state.
  const CHIP_GROUPS = {
    chkOres: { containerId: "oreChipsContainer", typesKey: "oreTypes" },
    chkSpawners: { containerId: "spawnerChipsContainer", typesKey: "spawnerTypes" },
    chkStructures: { containerId: "structureChipsContainer", typesKey: "structureTypes" }
  };

  // Master Category Toggles (Ores, Spawners, Structures, Chests, Biomes)
  ["chkBiomes", "chkOres", "chkSpawners", "chkStructures", "chkChests"].forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("change", (e) => {
      const key = id.replace("chk", "").toLowerCase();
      activeFilters[key] = e.target.checked;

      const group = CHIP_GROUPS[id];
      if (group) {
        const container = document.getElementById(group.containerId);
        const chips = Array.from(container.querySelectorAll(".filter-chip"));
        chips.forEach((c) => c.classList.toggle("active", e.target.checked));
        activeFilters[group.typesKey] = e.target.checked ? chips.map((c) => c.dataset.id) : [];
      }

      // Also open corresponding subfilter drawer when enabled
      if (key === "ores" && e.target.checked) document.getElementById("subOres").classList.add("open");
      if (key === "spawners" && e.target.checked) document.getElementById("subSpawners").classList.add("open");
      if (key === "structures" && e.target.checked) document.getElementById("subStructures").classList.add("open");

      // Keep the Chunkbase-style icon strip's active border in sync,
      // whichever way the underlying checkbox got toggled.
      const iconBtn = document.querySelector(`.feature-icon-btn[data-for="${id}"]`);
      if (iconBtn) iconBtn.classList.toggle("active", e.target.checked);

      refreshMap();
    });
  });

  // Feature icon strip: clicking an icon just clicks its real checkbox,
  // so every existing filter/refresh behavior above fires unchanged.
  document.querySelectorAll(".feature-icon-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const checkbox = document.getElementById(btn.dataset.for);
      if (checkbox) checkbox.click();
    });
  });

  // Keep the Chunkbase-style icon strip's active border synced whenever a
  // checkbox is toggled programmatically instead of via a real click.
  function syncFeatureIcon(chkId) {
    const iconBtn = document.querySelector(`.feature-icon-btn[data-for="${chkId}"]`);
    if (iconBtn) iconBtn.classList.toggle("active", document.getElementById(chkId).checked);
  }

  // Quick Preset Chips
  document.getElementById("presetDiamonds").addEventListener("click", () => {
    // Turn on Ores
    document.getElementById("chkOres").checked = true;
    syncFeatureIcon("chkOres");
    activeFilters.ores = true;
    document.getElementById("subOres").classList.add("open");

    // Select only diamond and debris chips
    const container = document.getElementById("oreChipsContainer");
    container.querySelectorAll(".filter-chip").forEach((c) => {
      const id = c.dataset.id.toLowerCase();
      if (id.includes("diamond") || id.includes("ancient_debris")) {
        c.classList.add("active");
      } else {
        c.classList.remove("active");
      }
    });
    activeFilters.oreTypes = Array.from(container.querySelectorAll(".filter-chip.active")).map((c) => c.dataset.id);
    refreshMap();
    showToast("Filtering: Diamonds & Debris");
  });

  document.getElementById("presetSpawners").addEventListener("click", () => {
    document.getElementById("chkSpawners").checked = true;
    syncFeatureIcon("chkSpawners");
    activeFilters.spawners = true;
    document.getElementById("subSpawners").classList.add("open");
    // Clear sub-filters so all spawners show
    const container = document.getElementById("spawnerChipsContainer");
    container.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
    activeFilters.spawnerTypes = [];
    refreshMap();
    showToast("Displaying All Spawners");
  });

  document.getElementById("presetStructures").addEventListener("click", () => {
    document.getElementById("chkStructures").checked = true;
    syncFeatureIcon("chkStructures");
    activeFilters.structures = true;
    document.getElementById("subStructures").classList.add("open");
    const container = document.getElementById("structureChipsContainer");
    container.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
    activeFilters.structureTypes = [];
    refreshMap();
    showToast("Displaying Structures");
  });

  document.getElementById("presetClear").addEventListener("click", () => {
    ["chkBiomes", "chkOres", "chkSpawners", "chkStructures", "chkChests"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.checked = false;
      const iconBtn = document.querySelector(`.feature-icon-btn[data-for="${id}"]`);
      if (iconBtn) iconBtn.classList.remove("active");
    });
    activeFilters.biomes = false;
    activeFilters.ores = false;
    activeFilters.spawners = false;
    activeFilters.structures = false;
    activeFilters.chests = false;
    activeFilters.oreTypes = [];
    activeFilters.spawnerTypes = [];
    activeFilters.structureTypes = [];

    document.querySelectorAll(".filter-chip.active").forEach((c) => c.classList.remove("active"));
    refreshMap();
    showToast("Cleared All Layers");
  });

  // Refresh Map & Render Markers
  // Only ever requests what is currently on screen (padded viewport bbox),
  // not the whole world — the world can hold tens of thousands of chunks
  // and millions of ore blocks, so an unbounded fetch is what causes lag.
  // Biomes and markers are fetched in parallel (not one-after-the-other) —
  // when both layers are on, this halves the wait versus a serial round trip.
  let refreshToken = 0;
  async function refreshMap() {
    if (!currentWorld) return;
    const myToken = ++refreshToken;

    const hasMarkerLayer = activeFilters.ores || activeFilters.spawners || activeFilters.structures || activeFilters.chests;
    const hasAnyLayer = activeFilters.biomes || hasMarkerLayer;
    mapHintBanner.style.opacity = hasAnyLayer ? "0" : "1";

    const bounds = mapController.getBlockBounds();
    const bboxParams = `min_x=${bounds.minX}&max_x=${bounds.maxX}&min_z=${bounds.minZ}&max_z=${bounds.maxZ}`;

    const biomePromise = activeFilters.biomes
      ? fetch(`/api/map/biomes?dimension=${encodeURIComponent(currentDimension)}&${bboxParams}`)
          .then((r) => r.json())
          .catch((e) => { console.error("Error loading biomes:", e); return null; })
      : Promise.resolve(null);

    let markerPromise = Promise.resolve([]);
    if (hasMarkerLayer) {
      let url = `/api/map/markers?dimension=${encodeURIComponent(currentDimension)}&${bboxParams}`;
      url += `&include_ores=${activeFilters.ores}`;
      url += `&include_spawners=${activeFilters.spawners}`;
      url += `&include_structures=${activeFilters.structures}`;
      url += `&include_chests=${activeFilters.chests}`;
      if (activeFilters.oreTypes.length) url += `&ores=${encodeURIComponent(activeFilters.oreTypes.join(","))}`;
      if (activeFilters.spawnerTypes.length) url += `&spawners=${encodeURIComponent(activeFilters.spawnerTypes.join(","))}`;
      if (activeFilters.structureTypes.length) url += `&structures=${encodeURIComponent(activeFilters.structureTypes.join(","))}`;

      markerPromise = fetch(url)
        .then((r) => r.json())
        .catch((e) => { console.error("Error loading markers:", e); return []; });
    }

    const [biomes, markers] = await Promise.all([biomePromise, markerPromise]);
    if (myToken !== refreshToken) return;

    if (activeFilters.biomes) {
      mapController.renderBiomes(biomes || []);
    } else {
      mapController.clearBiomes();
    }

    if (hasMarkerLayer) {
      mapController.renderMarkers(markers);
    } else {
      mapController.clearAllMarkers();
    }
  }

  // Scanning Controls
  btnScan.addEventListener("click", () => startScan(false));
  btnForceRescan.addEventListener("click", () => {
    if (confirm("This clears all indexed data for the current dimension and rescans it from scratch. Continue?")) {
      startScan(true);
    }
  });
  btnCancelScan.addEventListener("click", cancelScan);

  async function startScan(forceRescan) {
    try {
      const res = await fetch("/api/worlds/scan/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force_rescan: forceRescan, dimension_id: currentDimension })
      });
      const data = await res.json();
      if (res.ok) {
        scanBar.style.display = "flex";
        btnCancelScan.style.display = "inline-flex";
        pollProgress();
      } else {
        alert(data.detail || "Could not start scan.");
      }
    } catch (e) {
      console.error("Error starting scan:", e);
    }
  }

  async function cancelScan() {
    await fetch("/api/worlds/scan/cancel", { method: "POST" });
  }

  function pollProgress() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(async () => {
      try {
        const res = await fetch("/api/worlds/scan/status");
        const status = await res.json();

        scanProgressFill.style.width = `${status.percentage}%`;
        scanPercentEl.innerText = `${status.percentage}%`;
        scanStatusEl.innerText = status.status_message;

        if (!status.is_scanning) {
          clearInterval(pollInterval);
          btnCancelScan.style.display = "none";
          setTimeout(() => {
            scanBar.style.display = "none";
          }, 3000);
          await updateStats();
          await loadFilterOptions();
          await refreshMap();
        }
      } catch (e) {
        console.error("Error polling scan status:", e);
      }
    }, 800);
  }

  // Update category badge counts on the Layers card.
  async function updateStats() {
    try {
      const res = await fetch("/api/stats");
      const stats = await res.json();
      if (!stats) return;

      document.getElementById("countOres").innerText = stats.ore_veins_count || 0;
      document.getElementById("countSpawners").innerText = stats.spawners_count || 0;
      document.getElementById("countStructures").innerText = stats.structures_count || 0;
      document.getElementById("countChests").innerText = stats.chests_count || 0;
      document.getElementById("countBiomes").innerText = stats.chunks_count || 0;
    } catch (e) {
      console.error("Error updating stats:", e);
    }
  }

  // Search Input
  let searchDebounce = null;
  searchInput.addEventListener("input", (e) => {
    clearTimeout(searchDebounce);
    const query = e.target.value.trim();
    if (!query) {
      searchResults.style.display = "none";
      searchResults.innerHTML = "";
      return;
    }
    searchDebounce = setTimeout(() => doSearch(query), 250);
  });

  async function doSearch(query) {
    try {
      const res = await fetch(`/api/search?query=${encodeURIComponent(query)}&dimension=${encodeURIComponent(currentDimension)}`);
      const items = await res.json();
      searchResults.innerHTML = "";
      if (!items.length) {
        searchResults.style.display = "none";
        return;
      }
      searchResults.style.display = "flex";
      items.slice(0, 15).forEach((item) => {
        const div = document.createElement("div");
        div.className = "search-item";
        div.innerHTML = `
          <div>
            <div style="font-weight: 600; color: #fff;">${item.name}</div>
            <div style="font-size: 10px; color: var(--text-muted);">${item.category.toUpperCase()}</div>
          </div>
          <div class="search-item-coords">${item.x}, ${item.y}, ${item.z}</div>
        `;
        div.addEventListener("click", () => {
          mapController.jumpTo(item.x, item.z, 0);
          mapController.onLocationSelect(item);
          searchResults.style.display = "none";
        });
        searchResults.appendChild(div);
      });
    } catch (e) {
      console.error("Search error:", e);
    }
  }

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".search-wrapper")) {
      searchResults.style.display = "none";
    }
  });

  // Nearest Finder
  const btnFindNearest = document.getElementById("btnFindNearest");
  const btnShowPlayer = document.getElementById("btnShowPlayer");

  function readPlayerCoords() {
    return {
      x: parseInt(document.getElementById("nearX").value) || 0,
      y: parseInt(document.getElementById("nearY").value) || 64,
      z: parseInt(document.getElementById("nearZ").value) || 0
    };
  }

  btnShowPlayer.addEventListener("click", () => {
    const { x, y, z } = readPlayerCoords();
    mapController.setPlayerMarker(x, z, y);
    mapController.jumpTo(x, z, 1);
    showToast(`Showing location: X ${x}, Y ${y}, Z ${z}`);
  });

  btnFindNearest.addEventListener("click", async () => {
    const type = document.getElementById("nearestType").value;
    const subtype = document.getElementById("nearestSubtype").value.trim() || null;
    const { x, y, z } = readPlayerCoords();
    const maxDist = parseInt(document.getElementById("nearMaxDist").value) || 50000;

    mapController.setPlayerMarker(x, z, y);

    let url = `/api/search/nearest?feature_type=${type}&x=${x}&y=${y}&z=${z}&dimension=${encodeURIComponent(currentDimension)}&max_distance=${maxDist}`;
    if (subtype) url += `&subtype=${encodeURIComponent(subtype)}`;

    const resCard = document.getElementById("nearestResultCard");
    try {
      const res = await fetch(url);
      const data = await res.json();
      if (data) {
        resCard.style.display = "block";
        document.getElementById("nearestResultTitle").innerText = data.name;
        document.getElementById("nearestResultCoords").innerText = `X: ${data.x}  Y: ${data.y}  Z: ${data.z}`;
        document.getElementById("nearestResultDist").innerText = `Distance: ${data.distance.toLocaleString()} blocks away`;

        document.getElementById("btnJumpNearest").onclick = () => {
          mapController.jumpTo(data.x, data.z, 1);
          mapController.onLocationSelect(data);
        };
      } else {
        resCard.style.display = "block";
        document.getElementById("nearestResultTitle").innerText = "No Feature Found";
        document.getElementById("nearestResultCoords").innerText = "";
        document.getElementById("nearestResultDist").innerText = `No ${type} within ${maxDist} blocks.`;
      }
    } catch (e) {
      console.error("Error finding nearest:", e);
    }
  });

  // Command Deck: exclusive accordion. Clicking a card's header opens it
  // and closes the others; clicking an already-open card's header closes it.
  document.querySelectorAll(".deck-card-header").forEach((header) => {
    header.addEventListener("click", () => {
      const card = header.closest(".deck-card");
      const wasOpen = card.classList.contains("open");
      document.querySelectorAll(".deck-card").forEach((c) => c.classList.remove("open"));
      if (!wasOpen) card.classList.add("open");
    });
  });

  document.getElementById("btnGitDump").addEventListener("click", async () => {
    try {
      const res = await fetch("/api/export/git_dump", { method: "POST" });
      const data = await res.json();
      if (data.status === "success") {
        showToast("Git Dump Created (world_data.json)!");
      } else {
        alert(data.message || "Failed to create dump.");
      }
    } catch (e) {
      console.error("Git dump error:", e);
    }
  });

  // Select World Manually
  const worldPathInput = document.getElementById("worldPathInput");
  document.getElementById("btnSelectWorld").addEventListener("click", async () => {
    const path = worldPathInput.value.trim();
    if (!path) {
      worldPathInput.focus();
      return;
    }
    try {
      const res = await fetch("/api/worlds/select", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: path })
      });
      const data = await res.json();
      if (res.ok) {
        await loadCurrentWorld();
        showToast("World Loaded Successfully");
      } else {
        alert(data.detail || "Invalid world path.");
      }
    } catch (e) {
      console.error("Error selecting world:", e);
    }
  });

  // Initial Load
  loadCurrentWorld();
});
