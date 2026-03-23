import pytest
import os
import json
from database.persistence import log_task_event, register_artifact
from pipeline.queue.database import get_session, create_db_and_tables, reset_engine, get_engine
from pipeline.queue.repository import TaskRepository
from pipeline.queue.models import TaskSource

@pytest.fixture(autouse=True)
def setup_db():
    # 使用測試資料庫路徑
    test_db = os.path.abspath("data/test_task_queue.db")
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except:
            pass

    # 確保目錄存在
    os.makedirs(os.path.dirname(test_db), exist_ok=True)

    # 重置 engine 並手動建立 engine 指向測試庫
    reset_engine()
    engine = get_engine(test_db)
    create_db_and_tables(engine)

    yield

    reset_engine()
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except:
            pass

def test_task_events():
    # 建立一個測試任務
    with get_session() as session:
        repo = TaskRepository(session)
        task = repo.create_task(title="Test Task", video_id="test-vid-1", source=TaskSource.INTERNAL)
        task_id = task.id

    # 測試 log_task_event
    log_task_event(task_id, 'started', '{"progress": 0}')

    # 驗證
    with get_session() as session:
        repo = TaskRepository(session)
        events = repo.get_events(task_id)
        assert len(events) == 1
        assert events[0].event_type == 'started'
        assert json.loads(events[0].event_metadata) == {"progress": 0}

def test_register_artifact():
    # 建立一個測試任務
    with get_session() as session:
        repo = TaskRepository(session)
        task = repo.create_task(title="Test Task 2", video_id="test-vid-2", source=TaskSource.INTERNAL)
        task_id = task.id

    # 測試 register_artifact
    register_artifact(task_id, 'json', '/path/to/file')

    # 驗證
    with get_session() as session:
        repo = TaskRepository(session)
        artifacts = repo.get_artifacts(task_id)
        assert len(artifacts) == 1
        assert artifacts[0].format == 'json'
        assert artifacts[0].path == '/path/to/file'
