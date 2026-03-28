"""端對端 Smoke Test：API 提交 → Scheduler 推進 → DONE。"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine
from starlette.testclient import TestClient

from pipeline.queue.models import StageType, Task, TaskStatus
from pipeline.queue.repository import TaskRepository


_test_engine = None


def _reset_test_engine() -> None:
    global _test_engine
    if _test_engine is not None:
        _test_engine.dispose()
    _test_engine = None


def _test_get_engine():
    global _test_engine
    if _test_engine is None:
        _test_engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return _test_engine


def _test_create_db_and_tables() -> None:
    engine = _test_get_engine()
    from pipeline.queue.models import Task, StageTask, TaskEvent, TaskArtifact  # noqa: F401
    from api.models import ApiKey, RefreshToken, User, Identity  # noqa: F401

    SQLModel.metadata.create_all(engine)


def _test_get_session() -> Session:
    return Session(_test_get_engine())


_mock_executors = {
    StageType.DOWNLOAD: MagicMock(),
    StageType.TRANSCRIBE: MagicMock(),
    StageType.PROOFREAD: MagicMock(),
    StageType.POSTPROCESS: MagicMock(),
}


@pytest.fixture(autouse=True)
def reset_mock_executors():
    for executor in _mock_executors.values():
        executor.reset_mock()
    yield


@pytest.fixture
def smoke_client(tmp_path):
    """帶 lifespan 的完整 app TestClient，使用 mock executor。"""
    _reset_test_engine()
    _test_create_db_and_tables()

    with (
        patch("pipeline.queue.database.get_engine", _test_get_engine),
        patch("pipeline.queue.database.get_session", _test_get_session),
        patch("pipeline.queue.database.create_db_and_tables", _test_create_db_and_tables),
        patch("api_server.get_session", _test_get_session),
        patch("api_server.create_db_and_tables", _test_create_db_and_tables),
        patch(
            "pipeline.queue.scheduler.TaskScheduler.build_default_executors",
            return_value=_mock_executors,
        ),
        patch("pipeline.queue.scheduler.acquire_gpu_lock", return_value=999),
        patch("pipeline.queue.scheduler.release_gpu_lock", return_value=None),
        patch("api.routers.tasks.log_task_event", lambda *a, **kw: None),
        patch("api.routers.tasks.OUTPUT_BASE", tmp_path),
        patch("pipeline.queue.playlist_sync.PlaylistSyncWorker.start", return_value=None),
        patch("pipeline.queue.playlist_sync.PlaylistSyncWorker.stop", return_value=None),
    ):
        from api_server import app

        with TestClient(app) as client:
            yield client

    _reset_test_engine()


def _run_process_next() -> None:
    """同步執行一次 scheduler._process_next()。"""
    import api_server

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(api_server._scheduler._process_next())
    finally:
        loop.close()


class TestSmokeE2E:
    """Smoke E2E：API → Pipeline → DONE。"""

    def test_submit_and_process_to_done(self, smoke_client):
        """提交任務並推進 4 輪至 DONE。"""
        payload = {
            "action": "queue",
            "target": "smoke_test_vid",
            "title": "Smoke E2E Test",
            "source": "internal",
        }
        response = smoke_client.post("/api/task", json=payload)
        assert response.status_code == 200
        data = response.json()
        task_id = data["task_id"]
        assert task_id is not None

        for _ in range(4):
            _run_process_next()

        assert _mock_executors[StageType.DOWNLOAD].call_count == 1
        assert _mock_executors[StageType.TRANSCRIBE].call_count == 1
        assert _mock_executors[StageType.PROOFREAD].call_count == 1
        assert _mock_executors[StageType.POSTPROCESS].call_count == 1

        with _test_get_session() as session:
            task = session.get(Task, task_id)
            assert task is not None
            assert task.status == TaskStatus.DONE

    def test_scheduler_is_running(self, smoke_client):
        """驗證 lifespan 啟動了 scheduler。"""
        import api_server

        assert api_server._scheduler is not None
        assert api_server._scheduler._running is True

    def test_queue_status_endpoint(self, smoke_client):
        """GET /api/queue/status 應回傳 scheduler_running=true。"""
        response = smoke_client.get("/api/queue/status")
        assert response.status_code == 200
        data = response.json()
        assert data["scheduler_running"] is True

    def test_submit_and_partial_process(self, smoke_client):
        """提交任務後只推進 1 輪，任務應尚未 DONE，且 TRANSCRIBE 已 fan-out。"""
        payload = {
            "action": "queue",
            "target": "partial_test_vid",
            "title": "Partial Process Test",
            "source": "internal",
        }
        response = smoke_client.post("/api/task", json=payload)
        assert response.status_code == 200
        task_id = response.json()["task_id"]

        _run_process_next()

        with _test_get_session() as session:
            task = session.get(Task, task_id)
            assert task.status != TaskStatus.DONE

        with _test_get_session() as session:
            repo = TaskRepository(session)
            stages = repo.get_stages_for_task(task_id)
            stage_types = {s.stage for s in stages}
        assert StageType.TRANSCRIBE in stage_types
