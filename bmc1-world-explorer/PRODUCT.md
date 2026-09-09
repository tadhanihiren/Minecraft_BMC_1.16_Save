# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Solo player/owner of the "golida" Better MC [FORGE] BMC1 v62 (Minecraft 1.16.5) world, running the tool locally on Windows to plan exploration and mining without spoiling surprises by wandering blind.

## Product Purpose

Offline, read-only scanner and map viewer for a single Minecraft 1.16.5 world save: indexes ores, spawners, structures, chests, and biomes into a local SQLite file and renders them on an interactive Leaflet map so the player can plan routes and find the nearest feature of interest.

## Positioning

Purpose-built for this exact modpack (BMC1 v62) and world, with incremental region/chunk caching so re-scans are near-instant — a generic map viewer or the vanilla F3 debug screen can't do either.

## Operating Context

Runs as a local FastAPI server (`run.bat` / `python -m app.main`) opened in a normal desktop browser window on Windows. No internet connection at runtime — all assets (Leaflet, fonts, icons) must stay bundled/CSS-only.

## Capabilities and Constraints

- Never writes to the original world files (`rb` mode only).
- Single-user, single-world-at-a-time tool; no accounts, no network calls.
- All UI state lives in `frontend/js/app.js` + `frontend/js/map.js`; the DOM ids they query (`worldName`, `scanBar`, `chkOres`, `.filter-chip`, `.tab-btn[data-tab]`, etc.) are load-bearing and must be preserved by future visual passes.

## Brand Commitments

Name: "BMC1 World Explorer". Visual world (chosen 2026-09-08): blocky Minecraft-native inventory-GUI chrome — light-gray bevel panels, redstone-lever toggles, F3-debug-style coordinate HUD, item-tooltip-style selection card, XP-bar scan progress, achievement-toast notifications. Pure CSS, no external fonts/images.

## Product Principles

- Read-only safety is non-negotiable — never let a UI affordance imply write access to the save.
- Layers stay opt-in by default; the map must never auto-clutter with every feature type on load.
- Keep it a single-file, offline, zero-dependency-at-runtime tool — no CDN fonts, no network fetches beyond the local API.
