"""
history.py
Persistent audit trail of redaction sessions, backed by SQLite.

Deliberate privacy design decision: this database stores WHAT was
found (label, page, whether it was confirmed for redaction) but NEVER
the actual matched text (the real PAN, Aadhaar number, etc). A
growing local database full of real PII values would itself become
exactly the kind of liability this tool exists to prevent - "we have
an audit log of every PAN we've ever redacted" is not meaningfully
safer than not redacting at all, if that log is sitting in a plain
SQLite file. Storing only labels and counts gives a genuinely useful
compliance trail (what kinds of PII were found, how often, whether
they were acted on) without recreating the risk.
"""

import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "maskfin_history.db")


def init_db(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            backend TEXT NOT NULL,
            total_detected INTEGER NOT NULL,
            total_redacted INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            page INTEGER NOT NULL,
            label TEXT NOT NULL,
            redacted INTEGER NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    conn.commit()
    conn.close()


def log_session(filename: str, backend: str, detections: list, confirmed_ids: set,
                 db_path: str = DB_PATH) -> int:
    """
    Record a redaction session. `detections` is the full scan result
    (list of dicts with id/page/label/text/box); `confirmed_ids` is the
    set of detection ids the user actually approved for redaction.
    Only label/page/redacted-flag are stored - never the 'text' field.
    Returns the new session's id.
    """
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    total_detected = len(detections)
    total_redacted = len(confirmed_ids)
    timestamp = datetime.now(timezone.utc).isoformat()

    cur.execute(
        "INSERT INTO sessions (filename, timestamp, backend, total_detected, total_redacted) "
        "VALUES (?, ?, ?, ?, ?)",
        (filename, timestamp, backend, total_detected, total_redacted),
    )
    session_id = cur.lastrowid

    for d in detections:
        cur.execute(
            "INSERT INTO items (session_id, page, label, redacted) VALUES (?, ?, ?, ?)",
            (session_id, d["page"], d["label"], 1 if d["id"] in confirmed_ids else 0),
        )

    conn.commit()
    conn.close()
    return session_id


def get_all_sessions(db_path: str = DB_PATH) -> list:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM sessions ORDER BY timestamp DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session_items(session_id: int, db_path: str = DB_PATH) -> list:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM items WHERE session_id = ? ORDER BY page, label", (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    fake_detections = [
        {"id": 0, "page": 1, "label": "PAN", "text": "ABCDE1234F", "box": (0, 0, 1, 1)},
        {"id": 1, "page": 1, "label": "IFSC", "text": "HDFC0001234", "box": (0, 0, 1, 1)},
    ]
    sid = log_session("test.pdf", "groq", fake_detections, confirmed_ids={0})
    print(f"Logged session {sid}")
    print("All sessions:", get_all_sessions())
    print("Items for this session:", get_session_items(sid))
