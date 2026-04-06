"""測試 /api/task action=queue 的任務提交入口。"""
import pytest
from pipeline.queue.repository import TaskRepository
from pipeline.queue.models import TaskStatus, TaskSource, StageType
from pipeline.queue.stage_runner import create_initial_stages


def test_queue_submission_creates_task_and_stage(db_session):
    """模擬 /api/task action=queue 的核心邏輯：建立 task + initial stage。"""
    repo = TaskRepository(db_session)

    # 模擬 API handler 的行為
    video_id = "submit_vid_001"
    title = "提交測試影片"
    source = TaskSource.EXTERNAL

    task = repo.create_task(
        title=title,
        video_id=video_id,
        source=source,
    )
    stage = create_initial_stages(db_session, task)

    assert task.id is not None
    assert task.status == TaskStatus.PENDING
    assert task.source == TaskSource.EXTERNAL
    assert task.priority == 0  # external = 0

    assert stage.stage == StageType.DOWNLOAD
    assert stage.status == TaskStatus.PENDING
    assert stage.task_id == task.id


def test_queue_submission_internal_priority(db_session):
    """內部任務提交時 priority=10。"""
    repo = TaskRepository(db_session)

    task = repo.create_task(
        title="Internal video",
        video_id="int_vid_001",
        source=TaskSource.INTERNAL,
    )
    stage = create_initial_stages(db_session, task)

    assert task.priority == 10
    assert stage.priority >= 10


def test_queue_submission_returns_ids(db_session):
    """提交後回傳 task_id 和 stage_id。"""
    repo = TaskRepository(db_session)
    task = repo.create_task(title="ID test", video_id="id_vid")
    stage = create_initial_stages(db_session, task)

    # 模擬 API response
    response = {
        "status": "queued",
        "task_id": task.id,
        "stage_id": stage.id,
        "video_id": "id_vid",
    }
    assert response["task_id"] is not None
    assert response["stage_id"] is not None
    assert response["status"] == "queued"


def test_playlist_submission_creates_parent_and_children(db_session):
    """播放清單提交：建立父任務 + 每集子任務 + initial stages。"""
    repo = TaskRepository(db_session)

    parent = repo.create_playlist_parent_task(
        playlist_id="PL_submit",
        playlist_title="測試播放清單",
        source=TaskSource.INTERNAL,
    )

    videos = [
        {"id": "v001", "title": "EP 001"},
        {"id": "v002", "title": "EP 002"},
        {"id": "v003", "title": "EP 003"},
    ]

    for v in videos:
        child = repo.create_child_task(
            parent_task_id=parent.id,
            title=v["title"],
            video_id=v["id"],
            playlist_id="PL_submit",
            source=TaskSource.INTERNAL,
        )
        create_initial_stages(db_session, child)

    children = repo.get_child_tasks(parent.id)
    assert len(children) == 3
    for child in children:
        assert child.parent_task_id == parent.id
        stages = repo.get_stages_for_task(child.id)
        assert len(stages) == 1
        assert stages[0].stage == StageType.DOWNLOAD
