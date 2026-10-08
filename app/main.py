import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api.routes import router
from app.retrieval.indexer import ensure_documents_indexed

logger = logging.getLogger(__name__)

INIT_SQL_PATH = Path(__file__).resolve().parent.parent / "docker" / "init.sql"


def _run_db_init():
    """Run docker/init.sql against the connected PostgreSQL database.

    Creates tables and seeds sample data when the DB is empty (all statements
    use IF NOT EXISTS / ON CONFLICT DO NOTHING so this is idempotent).
    Falls back silently when the DB is not yet reachable so the app still starts.
    """
    try:
        import psycopg
        if not INIT_SQL_PATH.exists():
            return
        sql = INIT_SQL_PATH.read_text()
        with psycopg.connect(settings.database_url, connect_timeout=5) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(sql)
        logger.info("PostgreSQL schema initialised from docker/init.sql")
    except Exception as exc:
        logger.warning(f"DB init skipped (DB not yet reachable): {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _run_db_init()
    # Auto-index any PDFs in data/raw into Qdrant at startup
    try:
        indexed = ensure_documents_indexed()
        if indexed > 0:
            logger.info(f"Startup: {indexed} document chunks available in vector store.")
        else:
            logger.warning("Startup: No documents indexed — RAG queries will return empty context.")
    except Exception as exc:
        logger.warning(f"Startup document indexing skipped: {exc}")
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-oriented Agentic Enterprise Knowledge Copilot",
    lifespan=lifespan,
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