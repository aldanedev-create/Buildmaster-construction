import sqlite3
import json
import os
from contextlib import contextmanager
from config.config import Config

@contextmanager
def get_db():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize database with schema"""
    os.makedirs(os.path.dirname(Config.DATABASE_PATH) or ".", exist_ok=True)
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sql", "construction.sql")
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = f.read()
    
    with get_db() as conn:
        conn.executescript(schema)
        _run_light_migrations(conn)

def _run_light_migrations(conn):
    """Keep existing local databases aligned with the current schema."""
    def columns(table):
        return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}

    payment_columns = columns("payments")
    for column, column_type in {
        "payer_email": "TEXT",
        "bank_account_name": "TEXT",
        "bank_account_number": "TEXT",
        "verified_by": "INTEGER",
        "verified_at": "TIMESTAMP",
        "admin_notes": "TEXT",
    }.items():
        if column not in payment_columns:
            conn.execute(f"ALTER TABLE payments ADD COLUMN {column} {column_type}")

def get_db_connection():
    """Compatibility helper for older modules."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def query_db(sql, params=None, one=False):
    """Compatibility helper for older modules."""
    with get_db() as conn:
        cursor = conn.execute(sql, params or [])
        if sql.lstrip().upper().startswith("SELECT"):
            rows = cursor.fetchall()
            if one:
                return dict(rows[0]) if rows else None
            return [dict(row) for row in rows]
        return cursor.lastrowid

def query_one(sql, params=None):
    """Execute query and return single row"""
    with get_db() as conn:
        cursor = conn.execute(sql, params or [])
        row = cursor.fetchone()
        return dict(row) if row else None

def query_all(sql, params=None):
    """Execute query and return all rows"""
    with get_db() as conn:
        cursor = conn.execute(sql, params or [])
        return [dict(row) for row in cursor.fetchall()]

def execute(sql, params=None):
    """Execute insert/update/delete and return last row id"""
    with get_db() as conn:
        cursor = conn.execute(sql, params or [])
        return cursor.lastrowid

def execute_many(sql, params_list):
    """Execute multiple inserts"""
    with get_db() as conn:
        cursor = conn.executemany(sql, params_list)
        return cursor.rowcount
