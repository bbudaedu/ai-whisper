"""QUEUE-01: 系統提供異步任務佇列，任務提交後排隊等待 GPU 資源。"""
import pytest
from pipeline.queue.models import Task, StageTask, TaskStatus, TaskSource, StageType

def test_enqueue_pending(db_session):
    """任務提交後狀態為 pending。"""
    from pipeline.queue.repository import TaskRepository

    repo = TaskRepository(db_session)
    task = repo.create_task(title="Queue test", video_id="vid_001")

    assert task.status == TaskStatus.PENDING


def test_task_persisted_in_sqlite(db_session):
    """任務寫入 SQLite 後可被讀取。"""
    from pipeline.queue.repository import TaskRepository

    repo = TaskRepository(db_session)
    repo.create_task(title="Persist test", video_id="vid_002")

    task = repo.get_task_by_video_id("vid_002")
    assert task is not None
    assert task.title == "Persist test"


def test_create_task_smoke(db_session):
    """煙霧測試：可以建立 Task 並從 DB 讀回。"""
    task = Task(
        title="測試影片",
        video_id="abc123",
        playlist_id="pl_001",
        source=TaskSource.INTERNAL,
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    assert task.id is not None
    assert task.status == TaskStatus.PENDING
    assert task.source == TaskSource.INTERNAL
    assert task.video_id == "abc123"

def test_create_stage_task_smoke(db_session):
    """煙霧測試：可以建立 StageTask 並關聯到 Task。"""
    task = Task(title="測試", video_id="xyz789")
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    stage = StageTask(
        task_id=task.id,
        stage=StageType.DOWNLOAD,
        status=TaskStatus.PENDING,
        source=task.source,
        priority=task.priority,
    )
    db_session.add(stage)
    db_session.commit()
    db_session.refresh(stage)

    assert stage.id is not None
    assert stage.task_id == task.id
    assert stage.stage == StageType.DOWNLOAD

def test_stage_task_output_payload(db_session):
    """煙霧測試：output_payload 可儲存與讀取 stage 輸出資料。"""
    task = Task(title="Payload test", video_id="pl_test")
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    stage = StageTask(task_id=task.id, stage=StageType.DOWNLOAD)
    stage.set_output({"audio_path": "/tmp/test.m4a", "episode_dir": "/tmp/ep001"})
    db_session.add(stage)
    db_session.commit()
    db_session.refresh(stage)

    output = stage.get_output()
    assert output["audio_path"] == "/tmp/test.m4a"
    assert output["episode_dir"] == "/tmp/ep001"

def test_stage_task_next_retry_at(db_session):
    """煙霧測試：next_retry_at 欄位可設定與讀取。"""
    from datetime import datetime, timedelta
    task = Task(title="Retry at test", video_id="retry_at")
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    future = datetime.utcnow() + timedelta(seconds=30)
    stage = StageTask(task_id=task.id, stage=StageType.TRANSCRIBE, next_retry_at=future)
    db_session.add(stage)
    db_session.commit()
    db_session.refresh(stage)

    assert stage.next_retry_at is not None
    assert stage.next_retry_at >= datetime.utcnow()
