import os
import psycopg
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise RuntimeError("DATABASE_URL environment variable is not set!")
        conninfo = db_url if "sslmode" in db_url else db_url + "?sslmode=require"
        _pool = ConnectionPool(
            conninfo=conninfo,
            min_size=1,
            max_size=5,
            timeout=30,
            kwargs={"row_factory": dict_row},
        )
    return _pool


def get_db():
    return get_pool().getconn()


def release_db(conn):
    get_pool().putconn(conn)


def init_db():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            print("[DB] Threads table initialized.")
    finally:
        release_db(conn)
