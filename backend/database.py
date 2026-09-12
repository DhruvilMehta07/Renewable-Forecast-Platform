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
        CREATE TABLE IF NOT EXISTS forecast_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_time TEXT NOT NULL,
            created_at TEXT NOT NULL,
            forecast_json TEXT NOT NULL,
            site_json TEXT,
            mode TEXT
        )
    """)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(forecast_runs)").fetchall()}
    if "site_json" not in columns:
        conn.execute("ALTER TABLE forecast_runs ADD COLUMN site_json TEXT")
    if "mode" not in columns:
        conn.execute("ALTER TABLE forecast_runs ADD COLUMN mode TEXT")
    conn.commit()
    conn.close()


def save_run(issue_time: str, forecast_rows: list, site: dict = None, mode: str = None):
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute(
        "INSERT INTO forecast_runs (issue_time, created_at, forecast_json, site_json, mode) VALUES (?, ?, ?, ?, ?)",
        (issue_time, datetime.now(timezone.utc).isoformat(), json.dumps(forecast_rows), json.dumps(site), mode),
    )
    conn.commit()
    conn.close()


def get_recent_runs(limit: int = 10):
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, issue_time, created_at, forecast_json, site_json, mode FROM forecast_runs ORDER BY id DESC LIMIT ?", (limit,)
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
