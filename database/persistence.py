import sqlite3
import os

def get_db_connection(db_path="database.db"):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path="database.db"):
    conn = get_db_connection(db_path)
    with open("database/schema.sql", "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

def log_task_event(task_id, event_type, metadata, db_path="database.db"):
    conn = get_db_connection(db_path)
    conn.execute(
        "INSERT INTO task_events (task_id, event_type, metadata) VALUES (?, ?, ?)",
        (task_id, event_type, metadata),
    )
    conn.commit()
    conn.close()

def register_artifact(task_id, format, path, db_path="database.db"):
    conn = get_db_connection(db_path)
    conn.execute(
        "INSERT INTO task_artifacts (task_id, format, path) VALUES (?, ?, ?)",
        (task_id, format, path),
    )
    conn.commit()
    conn.close()
