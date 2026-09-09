import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from contextlib import asynccontextmanager

from app.config import PROJECT_ROOT, DEFAULT_WORLD_PATH, HOST, PORT
from app.api.worlds import router as worlds_router, select_world, WorldSelectRequest
from app.api.map import router as map_router
from app.api.search import router as search_router
from app.api.stats import router as stats_router
from app.api.export import router as export_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-select world if present on startup
    if DEFAULT_WORLD_PATH and os.path.exists(DEFAULT_WORLD_PATH):
        try:
            select_world(WorldSelectRequest(path=DEFAULT_WORLD_PATH))
            print(f"[BMC1 Explorer] Auto-loaded world from: {DEFAULT_WORLD_PATH}")
        except Exception as e:
            print(f"[BMC1 Explorer] Could not auto-load world: {e}")
    yield

app = FastAPI(
    title="BMC1 World Explorer",
    description="Offline Read-Only Minecraft 1.16.5 BMC1 World Analyzer and Visualizer",
    version="1.0.0",
    lifespan=lifespan,
    default_response_class=ORJSONResponse
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(worlds_router)
app.include_router(map_router)
app.include_router(search_router)
app.include_router(stats_router)
app.include_router(export_router)

# Mount frontend directory for static assets and UI
frontend_dir = PROJECT_ROOT / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
