"""整合測試：排程器 + 佇列 + fan-out 端對端流程。"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from pipeline.queue.models import StageType, TaskStatus, TaskSource
from pipeline.queue.repository import TaskRepository
from pipeline.queue.scheduler import TaskScheduler
from pipeline.queue.stage_runner import create_initial_stages, enqueue_next_stage


@pytest.fixture
def integration_engine():
    """整合測試用 engine（in-memory）。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def integration_session(integration_engine):
    """整合測試用 Session。"""
    with Session(integration_engine) as session:
        yield session


def test_scheduler_processes_stage_with_mock_executor(integration_session):
    """排程器可以 claim 並執行一個 stage（使用 mock executor）。"""
    repo = TaskRepository(integration_session)
    task = repo.create_task(
        title="Integration test",
        video_id="int_test_001",
        source=TaskSource.INTERNAL,
    )
    create_initial_stages(integration_session, task, StageType.DOWNLOAD)

    mock_executor = MagicMock()
    executors = {StageType.DOWNLOAD: mock_executor}

    scheduler = TaskScheduler(
        session_factory=lambda: integration_session,
        stage_executors=executors,
        poll_interval=1,
    )

    asyncio.get_event_loop().run_until_complete(scheduler._process_next())
    assert mock_executor.call_count == 1


def test_enqueue_creates_task_and_stages(integration_session):
    """建立任務 + 初始 stage，驗證 DB 狀態正確。"""
    repo = TaskRepository(integration_session)
    task = repo.create_task(
        title="佛教公案 001",
        video_id="vid_e2e_001",
        playlist_id="pl_001",
        source=TaskSource.INTERNAL,
    )
    dl_stage = create_initial_stages(integration_session, task, StageType.DOWNLOAD)

    assert task.id is not None
    assert task.status == TaskStatus.PENDING
    assert task.source == TaskSource.INTERNAL
    assert dl_stage.task_id == task.id
    assert dl_stage.stage == StageType.DOWNLOAD
    assert dl_stage.status == TaskStatus.PENDING
    assert repo.count_pending_stages() == 1


def test_complete_stage_triggers_fanout(integration_session):
    """完成 download stage 後自動建立 transcribe stage。"""
    repo = TaskRepository(integration_session)
    task = repo.create_task(title="Fanout", video_id="fanout_e2e")
    dl = create_initial_stages(integration_session, task, StageType.DOWNLOAD)

    repo.complete_stage(dl.id)
    integration_session.refresh(dl)

    next_stage = enqueue_next_stage(integration_session, dl)
    assert next_stage is not None
    assert next_stage.stage == StageType.TRANSCRIBE
    assert next_stage.status == TaskStatus.PENDING
    assert repo.count_pending_stages() == 1


@patch("pipeline.queue.scheduler.acquire_gpu_lock", return_value=None)
def test_scheduler_returns_stage_when_gpu_busy(
    mock_gpu_lock,
    integration_session,
):
    """GPU 忙碌時 transcribe stage 退回 pending。"""
    repo = TaskRepository(integration_session)
    task = repo.create_task(title="GPU busy test", video_id="gpubusy1")
    task_id = task.id
    create_initial_stages(integration_session, task, StageType.TRANSCRIBE)

    executors = {StageType.TRANSCRIBE: MagicMock()}
    scheduler = TaskScheduler(
        session_factory=lambda: integration_session,
        stage_executors=executors,
        poll_interval=1,
    )

    asyncio.get_event_loop().run_until_complete(scheduler._process_next())

    assert executors[StageType.TRANSCRIBE].call_count == 0

    stages = repo.get_stages_for_task(task_id)
    assert len(stages) == 1
    assert stages[0].status == TaskStatus.PENDING


def test_download_concurrency_limit(integration_session):
    """下載最多 2 併行，超過時退回 pending。"""
    repo = TaskRepository(integration_session)

    tasks = []
    for i in range(3):
        t = repo.create_task(title=f"DL {i}", video_id=f"dl_{i}")
        create_initial_stages(integration_session, t, StageType.DOWNLOAD)
        tasks.append(t)

    claimed1 = repo.claim_next_stage(stage_filter=StageType.DOWNLOAD)
    claimed2 = repo.claim_next_stage(stage_filter=StageType.DOWNLOAD)
    assert claimed1 is not None
    assert claimed2 is not None

    running = repo.get_running_stages(stage_filter=StageType.DOWNLOAD)
    assert len(running) == 2

    stages = repo.get_stages_for_task(tasks[2].id)
    assert any(s.status == TaskStatus.PENDING for s in stages)
