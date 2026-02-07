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
        _pool = ConnectionPool(
            conninfo=os.getenv("DATABASE_URL") + "?sslmode=require",
            min_size=2,
            max_size=10,
            timeout=30,
            kwargs={"row_factory": dict_row}
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
