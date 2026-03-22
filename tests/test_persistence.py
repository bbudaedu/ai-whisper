import pytest
import sqlite3
import os
from database.persistence import get_db_connection, init_db, log_task_event, register_artifact

@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists("database.db"):
        os.remove("database.db")
    init_db("database.db")
    yield
    if os.path.exists("database.db"):
        os.remove("database.db")

def test_wal_mode():
    conn = get_db_connection("database.db")
    cursor = conn.execute("PRAGMA journal_mode")
    mode = cursor.fetchone()[0]
    assert mode == "wal"
    conn.close()

def test_task_events():
    conn = get_db_connection("database.db")
    # Need to insert a dummy task first since event has FK constraint
    conn.execute("INSERT INTO tasks (id) VALUES ('task-1')")
    conn.commit()
    conn.close()

    log_task_event('task-1', 'started', '{}')

    conn = get_db_connection("database.db")
    row = conn.execute("SELECT * FROM task_events WHERE task_id = 'task-1'").fetchone()
    assert row is not None
    assert row['event_type'] == 'started'
    conn.close()

def test_register_artifact():
    conn = get_db_connection("database.db")
    conn.execute("INSERT INTO tasks (id) VALUES ('task-2')")
    conn.commit()
    conn.close()

    register_artifact('task-2', 'json', '/path/to/file')

    conn = get_db_connection("database.db")
    row = conn.execute("SELECT * FROM task_artifacts WHERE task_id = 'task-2'").fetchone()
    assert row is not None
    assert row['path'] == '/path/to/file'
    conn.close()
