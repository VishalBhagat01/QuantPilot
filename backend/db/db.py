"""PostgreSQL connection pool and database lifecycle management."""

import logging
from contextlib import contextmanager
import psycopg
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from backend.core.config import settings

logger = logging.getLogger(__name__)

_pool: ConnectionPool | None = None
_db_checked: bool = False
_db_available: bool = False


def check_db_availability() -> bool:
    """Quick 3-second probe to check if the PostgreSQL database is reachable."""
    global _db_checked, _db_available
    if _db_checked:
        return _db_available

    db_url = settings.database_url
    if not db_url:
        _db_checked = True
        _db_available = False
        return False

    conninfo = db_url if "sslmode" in db_url else f"{db_url}?sslmode=require"
    try:
        with psycopg.connect(conninfo, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        _db_available = True
    except Exception as e:
        logger.warning(f"[DB] Connection probe failed: {e}")
        _db_available = False

    _db_checked = True
    return _db_available


def get_pool() -> ConnectionPool:
    """Retrieve or initialize the thread-safe connection pool."""
    global _pool
    if not check_db_availability():
        raise RuntimeError("Database host is currently unreachable or DATABASE_URL is invalid.")

    if _pool is None:
        db_url = settings.database_url
        conninfo = db_url if "sslmode" in db_url else f"{db_url}?sslmode=require"
        _pool = ConnectionPool(
            conninfo=conninfo,
            min_size=0,
            max_size=5,
            timeout=3,
            kwargs={"row_factory": dict_row},
        )
    return _pool


def get_db():
    """Acquire a connection from the pool."""
    return get_pool().getconn()


def release_db(conn):
    """Safely return a connection to the pool."""
    if _pool is not None and conn is not None:
        try:
            _pool.putconn(conn)
        except Exception:
            pass


@contextmanager
def db_session():
    """Context manager for safe, leak-free connection acquisition and release."""
    conn = get_db()
    try:
        yield conn
    finally:
        release_db(conn)


def init_db():
    """Initialize database schema, tables, and performance indexes."""
    if not check_db_availability():
        raise RuntimeError("Database unavailable, skipping init_db.")

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    user_id TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_threads_updated_at ON threads (updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_threads_user_id ON threads (user_id);
            """)
            conn.commit()
            
            # For existing installations, try to add user_id column if it doesn't exist
            try:
                cur.execute("ALTER TABLE threads ADD COLUMN user_id TEXT;")
                conn.commit()
                cur.execute("CREATE INDEX IF NOT EXISTS idx_threads_user_id ON threads (user_id);")
                conn.commit()
                logger.info("[DB] Added user_id column to existing threads table.")
            except Exception:
                conn.rollback() # Column already exists or error
                
            logger.info("[DB] Threads table and index ensured.")
