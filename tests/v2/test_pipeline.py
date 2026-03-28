"""Pipeline 狀態機測試：fan-out、失敗處理、retry。"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from pipeline.queue.models import StageTask, StageType, Task, TaskSource, TaskStatus
from pipeline.queue.repository import TaskRepository
from pipeline.queue.scheduler import TaskScheduler
from pipeline.queue.stage_runner import create_initial_stages


@pytest.fixture
def pipeline_engine():
    """獨立的 in-memory engine for pipeline tests。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from pipeline.queue.models import Task, StageTask, TaskEvent, TaskArtifact  # noqa: F401
    from api.models import ApiKey, RefreshToken, User, Identity  # noqa: F401

    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def pipeline_session_factory(pipeline_engine):
    """回傳 session factory callable。"""

    def factory():
        return Session(pipeline_engine)

    return factory


@pytest.fixture
def mock_executors():
    """每個 stage 對應一個 MagicMock executor。"""
    executors = {
        StageType.DOWNLOAD: MagicMock(),
        StageType.TRANSCRIBE: MagicMock(),
        StageType.PROOFREAD: MagicMock(),
        StageType.POSTPROCESS: MagicMock(),
    }
    yield executors


@pytest.fixture
def scheduler(pipeline_session_factory, mock_executors):
    """建立 TaskScheduler instance（不啟動 polling loop）。"""
    return TaskScheduler(
        session_factory=pipeline_session_factory,
        stage_executors=mock_executors,
    )


def _run_process_next(scheduler):
    """同步執行一次 _process_next()。"""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(scheduler._process_next())
    finally:
        loop.close()


def _create_task_with_initial_stage(session_factory):
    """建立任務並回傳 (task_id, stage_id)。"""
    session = session_factory()
    try:
        repo = TaskRepository(session)
        task = repo.create_task(
            title="Pipeline Test",
            video_id="pipeline_vid",
            source=TaskSource.INTERNAL,
        )
        stage = create_initial_stages(session, task)
        session.commit()
        session.refresh(task)
        session.refresh(stage)
        task_id = task.id
        stage_id = stage.id
    finally:
        session.close()
    return task_id, stage_id


class TestPipelineFanOut:
    """Pipeline 狀態轉換與 fan-out。"""

    def test_download_creates_transcribe_stage(
        self,
        scheduler,
        mock_executors,
        pipeline_session_factory,
    ):
        """DOWNLOAD 完成後應 fan-out 建立 TRANSCRIBE stage。"""
        with patch("pipeline.queue.scheduler.acquire_gpu_lock", return_value=999):
            with patch("pipeline.queue.scheduler.release_gpu_lock"):
                task_id, _ = _create_task_with_initial_stage(pipeline_session_factory)

                _run_process_next(scheduler)

                assert mock_executors[StageType.DOWNLOAD].call_count == 1

                with pipeline_session_factory() as session:
                    repo = TaskRepository(session)
                    stages = repo.get_stages_for_task(task_id)
                    stage_types = {s.stage for s in stages}
                    dl_stage_status = next(
                        (s.status for s in stages if s.stage == StageType.DOWNLOAD),
                        None,
                    )
                    tr_stage_status = next(
                        (s.status for s in stages if s.stage == StageType.TRANSCRIBE),
                        None,
                    )

                assert StageType.DOWNLOAD in stage_types
                assert StageType.TRANSCRIBE in stage_types
                assert dl_stage_status == TaskStatus.DONE
                assert tr_stage_status == TaskStatus.PENDING

    def test_full_pipeline_to_done(
        self,
        scheduler,
        mock_executors,
        pipeline_session_factory,
    ):
        """4 輪 _process_next 應將任務推進到 DONE。"""
        with patch("pipeline.queue.scheduler.acquire_gpu_lock", return_value=999):
            with patch("pipeline.queue.scheduler.release_gpu_lock"):
                task_id, _ = _create_task_with_initial_stage(pipeline_session_factory)

                for _ in range(4):
                    _run_process_next(scheduler)

                with pipeline_session_factory() as session:
                    task = session.get(Task, task_id)
                    assert task.status == TaskStatus.DONE

                for stage_type, executor in mock_executors.items():
                    assert executor.call_count == 1, f"{stage_type} not called"


class TestPipelineFailure:
    """Stage 拋出例外的處理。"""

    def test_stage_exception_marks_stage_failed(
        self,
        scheduler,
        mock_executors,
        pipeline_session_factory,
    ):
        """Stage executor 拋出例外時，stage status 應變為 FAILED 或 PENDING(retry)。"""
        mock_executors[StageType.DOWNLOAD].side_effect = RuntimeError("download error")

        with patch("pipeline.queue.scheduler.acquire_gpu_lock", return_value=999):
            with patch("pipeline.queue.scheduler.release_gpu_lock"):
                _, stage_id = _create_task_with_initial_stage(pipeline_session_factory)

                _run_process_next(scheduler)

                with pipeline_session_factory() as session:
                    stage = session.get(StageTask, stage_id)
                    assert stage.status in (TaskStatus.FAILED, TaskStatus.PENDING)
                    if stage.status == TaskStatus.FAILED:
                        assert stage.error_message != ""
