import logging
import queue
import re
import threading
from typing import Optional, Dict, Any

import psycopg
from psycopg.rows import dict_row

from app.config import settings

logger = logging.getLogger(__name__)


def mask_database_url(url: str) -> str:
    """Masks database password in connection strings for safe logging."""
    if not url:
        return ""
    try:
        return re.sub(r":([^@/:?]+)@", r":***@", url)
    except Exception:
        return "postgresql://***@***"


class ConnectionPool:
    """Thread-safe connection pool for PostgreSQL using psycopg 3."""

    def __init__(self, database_url: str, min_size: int = 1, max_size: int = 10, timeout: float = 5.0):
        self.database_url = database_url
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout
        self._pool: queue.Queue = queue.Queue(maxsize=max_size)
        self._lock = threading.Lock()
        self._created_count = 0
        self._closed = False

    def _create_connection(self, timeout: Optional[float] = None) -> psycopg.Connection:
        connect_timeout = int(timeout if timeout is not None else self.timeout)
        return psycopg.connect(
            self.database_url,
            row_factory=dict_row,
            connect_timeout=connect_timeout,
        )

    def get_connection(self, timeout: Optional[float] = None) -> psycopg.Connection:
        if self._closed:
            raise RuntimeError("Database connection pool is closed.")

        wait_timeout = timeout if timeout is not None else self.timeout

        # Try to retrieve an idle connection from the pool
        try:
            conn = self._pool.get_nowait()
            if not conn.closed:
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                    return conn
                except Exception:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    with self._lock:
                        self._created_count = max(0, self._created_count - 1)
            else:
                with self._lock:
                    self._created_count = max(0, self._created_count - 1)
        except queue.Empty:
            pass

        # Create a new connection if under max capacity
        with self._lock:
            if self._created_count < self.max_size:
                conn = self._create_connection(timeout=wait_timeout)
                self._created_count += 1
                return conn

        # Wait for an available connection from the pool
        try:
            conn = self._pool.get(timeout=wait_timeout)
            if conn.closed:
                with self._lock:
                    self._created_count = max(0, self._created_count - 1)
                return self._create_connection(timeout=wait_timeout)
            return conn
        except queue.Empty:
            raise TimeoutError(f"Database connection pool exhausted (max {self.max_size} connections).")

    def return_connection(self, conn: psycopg.Connection):
        if self._closed or conn.closed:
            try:
                conn.close()
            except Exception:
                pass
            with self._lock:
                self._created_count = max(0, self._created_count - 1)
            return

        try:
            if conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
                conn.rollback()
            self._pool.put_nowait(conn)
        except (queue.Full, Exception):
            try:
                conn.close()
            except Exception:
                pass
            with self._lock:
                self._created_count = max(0, self._created_count - 1)

    def close(self):
        self._closed = True
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Exception:
                pass
        with self._lock:
            self._created_count = 0


class PooledConnectionWrapper:
    """
    Context manager wrapper around a pooled connection.
    Ensures safe checkout, execution, commit/rollback, and return to the pool.
    Also forwards attribute access to the underlying connection for backwards compatibility.
    """

    def __init__(self, pool: ConnectionPool, timeout: Optional[float] = None):
        self._pool = pool
        self._timeout = timeout
        self._conn: Optional[psycopg.Connection] = None

    def __enter__(self) -> psycopg.Connection:
        self._conn = self._pool.get_connection(timeout=self._timeout)
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn is not None:
            if exc_type is not None:
                try:
                    self._conn.rollback()
                except Exception:
                    pass
            self._pool.return_connection(self._conn)
            self._conn = None

    def __getattr__(self, name: str):
        if self._conn is None:
            self._conn = self._pool.get_connection(timeout=self._timeout)
        return getattr(self._conn, name)


# Global Pool Instance
_global_pool: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()


def get_db_pool() -> ConnectionPool:
    global _global_pool
    if _global_pool is None:
        with _pool_lock:
            if _global_pool is None:
                _global_pool = ConnectionPool(
                    database_url=settings.database_url,
                    min_size=1,
                    max_size=10,
                    timeout=5.0,
                )
    return _global_pool


def init_db_pool():
    """Explicitly initializes database pool and logs connection attempt."""
    masked = mask_database_url(settings.database_url)
    logger.info(f"Initializing PostgreSQL connection pool against: {masked}")
    get_db_pool()


def close_db_pool():
    """Gracefully closes all pooled PostgreSQL connections."""
    global _global_pool
    if _global_pool is not None:
        with _pool_lock:
            if _global_pool is not None:
                logger.info("Closing PostgreSQL connection pool...")
                _global_pool.close()
                _global_pool = None


def get_connection(timeout: int = 2) -> PooledConnectionWrapper:
    """
    Returns a pooled PostgreSQL connection context manager.
    Compatible with existing `with get_connection() as conn:` pattern.
    """
    pool = get_db_pool()
    return PooledConnectionWrapper(pool=pool, timeout=float(timeout))


def test_connection(timeout: int = 2) -> bool:
    """Performs a health check probe against the database."""
    try:
        with get_connection(timeout=timeout) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 AS result")
                result = cursor.fetchone()
                return result["result"] == 1
    except Exception as exc:
        masked = mask_database_url(settings.database_url)
        logger.warning(f"PostgreSQL connection check failed for {masked}: {exc}")
        return False


def get_db_health() -> Dict[str, Any]:
    """Returns detailed health status of the database subsystem."""
    is_connected = test_connection(timeout=2)
    masked_url = mask_database_url(settings.database_url)
    pool = get_db_pool()
    return {
        "status": "connected" if is_connected else "unreachable",
        "url": masked_url,
        "pool_active": pool._created_count,
        "pool_max": pool.max_size,
    }
