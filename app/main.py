import gc
import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api.routes import router
from app.database.postgres import init_db_pool, close_db_pool, mask_database_url
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
        masked_url = mask_database_url(settings.database_url)
        logger.info(f"PostgreSQL schema initialised successfully on {masked_url} from docker/init.sql")
    except Exception as exc:
        masked_url = mask_database_url(settings.database_url)
        logger.warning(f"DB init skipped ({masked_url} not yet reachable): {exc}")


def _background_index():
    """
    Indexes all PDFs in data/raw/ into Qdrant in a background thread.
    Running after yield means the server is already up and Render's health
    check passes BEFORE the memory-intensive embedding work begins.
    This prevents OOM crashes on 512MB Render starter instances.
    """
    try:
        gc.collect()  # free any startup allocations before heavy work
        indexed = ensure_documents_indexed()
        if indexed > 0:
            logger.info(f"Background indexing complete: {indexed} chunks in vector store.")
        else:
            logger.warning("Background indexing: no documents found or indexing failed.")
    except Exception as exc:
        logger.error(f"Background indexing error: {exc}", exc_info=True)
    finally:
        gc.collect()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db_pool()
    _run_db_init()
    # Start indexing in a daemon background thread AFTER yield so the HTTP
    # server is live and can respond to health probes immediately.
    indexing_thread = threading.Thread(target=_background_index, daemon=True, name="startup-indexer")
    indexing_thread.start()
    yield
    close_db_pool()


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


@app.get("/")
async def root(request: Request):
    """Root endpoint: serves Web UI for browsers requesting HTML, JSON for API clients."""
    accept = request.headers.get("accept", "")
    index_file = static_dir / "index.html"
    if "text/html" in accept and "application/json" not in accept and index_file.exists():
        return FileResponse(str(index_file))
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "ui": "/ui",
    }