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
            forecast_json TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_run(issue_time: str, forecast_rows: list):
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute(
        "INSERT INTO forecast_runs (issue_time, created_at, forecast_json) VALUES (?, ?, ?)",
        (issue_time, datetime.now(timezone.utc).isoformat(), json.dumps(forecast_rows)),
    )
    conn.commit()
    conn.close()


def get_recent_runs(limit: int = 10):
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, issue_time, created_at FROM forecast_runs ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
