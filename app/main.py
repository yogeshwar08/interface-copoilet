from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api.routes import router


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-oriented Agentic Enterprise Knowledge Copilot",
)

# Enable CORS for cross-origin UI or API requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static asset directory
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(router)


@app.get("/")
@app.get("/ui")
@app.get("/dashboard")
async def serve_ui():
    """Serves the interactive web UI dashboard."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "ui": "/ui",
    }