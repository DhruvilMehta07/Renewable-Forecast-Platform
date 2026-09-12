"""
Minimal SQLite persistence - stores each forecast run so the dashboard can show
history, without needing a heavier DB for a single-site hackathon MVP.
"""

import sqlite3
import json
from datetime import datetime, timezone
import config


def init_db():
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS forecast_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            issue_time TEXT NOT NULL,
            created_at TEXT NOT NULL,
            forecast_json TEXT NOT NULL,
            site_json TEXT,
            mode TEXT
        )
    """)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(forecast_runs)").fetchall()}
    if "user_id" not in columns:
        conn.execute("ALTER TABLE forecast_runs ADD COLUMN user_id INTEGER")
    if "site_json" not in columns:
        conn.execute("ALTER TABLE forecast_runs ADD COLUMN site_json TEXT")
    if "mode" not in columns:
        conn.execute("ALTER TABLE forecast_runs ADD COLUMN mode TEXT")
    conn.commit()
    conn.close()


def create_user(username: str, display_name: str, password_hash: str):
    conn = sqlite3.connect(config.DB_PATH)
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, display_name, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (username, display_name, password_hash, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return get_user_by_id(cursor.lastrowid, conn)
    finally:
        conn.close()


def get_user_by_username(username: str):
    conn = sqlite3.connect(config.DB_PATH)
    try:
        return get_user_by_username_from_conn(username, conn)
    finally:
        conn.close()


def get_user_by_username_from_conn(username: str, conn):
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, username, display_name, password_hash, role, created_at FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int, conn=None):
    owns_connection = conn is None
    connection = conn or sqlite3.connect(config.DB_PATH)
    try:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT id, username, display_name, password_hash, role, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        if owns_connection:
            connection.close()


def save_run(issue_time: str, forecast_rows: list, site: dict = None, mode: str = None, user_id: int = None):
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute(
        "INSERT INTO forecast_runs (user_id, issue_time, created_at, forecast_json, site_json, mode) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, issue_time, datetime.now(timezone.utc).isoformat(), json.dumps(forecast_rows), json.dumps(site), mode),
    )
    conn.commit()
    conn.close()


def get_recent_runs(limit: int = 10, user_id: int = None):
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    if user_id is None:
        rows = []
    else:
        rows = conn.execute(
            "SELECT id, issue_time, created_at, forecast_json, site_json, mode FROM forecast_runs WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    conn.close()
    return [
        {
            "id": row["id"],
            "issue_time": row["issue_time"],
            "created_at": row["created_at"],
            "forecast": json.loads(row["forecast_json"]),
            "site": json.loads(row["site_json"]) if row["site_json"] else None,
            "mode": row["mode"],
        }
        for row in rows
    ]
